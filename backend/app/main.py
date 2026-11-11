from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from psycopg.errors import ForeignKeyViolation, UniqueViolation, CheckViolation, RestrictViolation
from .config import FRONTEND_ORIGIN, settings
from .db import connection, rows
from .schemas import *

logger = logging.getLogger('infraassess.semantic_search')

TABLES = {
 'locations': ('location','location_id',['location_code','name','address','region']),
 'categories': ('component_category','category_id',['category_code','name','description']),
 'components': ('component','component_id',['asset_tag','location_id','category_id','name','status','installed_on']),
 'technicians': ('technician','technician_id',['employee_code','full_name','email','specialty','active']),
 'assessments': ('assessment','assessment_id',['component_id','technician_id','assessed_at','health_score','condition_status','findings']),
 'incidents': ('incident','incident_id',['incident_number','reported_at','severity','status','title','description','resolved_at']),
 'work-orders': ('work_order','work_order_id',['work_order_number','incident_id','component_id','technician_id','work_type','status','planned_start','planned_end','completed_at','estimated_cost','completion_notes']),
 'maintenance-records': ('maintenance_record','maintenance_id',['work_order_id','technician_id','performed_at','action_taken','actual_cost','outcome']),
 'sensor-readings': ('sensor_reading','reading_id',['component_id','recorded_at','sensor_type','reading_value','unit']),
 'maintenance-alerts': ('maintenance_alert','alert_id',['component_id','assessment_id','alert_type','status','created_at','message']),
}

def db_error(exc):
    if isinstance(exc, (ForeignKeyViolation, RestrictViolation)): return HTTPException(409, 'This record is referenced by protected historical records.')
    if isinstance(exc, UniqueViolation): return HTTPException(409, 'A record with this unique identifier already exists.')
    if isinstance(exc, CheckViolation): return HTTPException(422, 'The record violates a database integrity rule.')
    return HTTPException(500, 'Database operation failed.')

def generic_list(key, limit, offset, search):
    table, pk, cols = TABLES[key]; where=''; params=[]
    if search:
        text_cols=[c for c in cols if c in ('name','title','description','asset_tag','incident_number','work_order_number','full_name','specialty')]
        if text_cols: where=' WHERE ' + ' OR '.join(f'CAST({c} AS text) ILIKE %s' for c in text_cols); params=['%'+search+'%']*len(text_cols)
    with connection() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT * FROM {table}{where} ORDER BY {pk} DESC LIMIT %s OFFSET %s', (*params,limit,offset)); return rows(cur)

def generic_get(key, item_id):
    table, pk, _=TABLES[key]
    with connection() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT * FROM {table} WHERE {pk}=%s',(item_id,)); result=rows(cur)
    if not result: raise HTTPException(404,'Record not found')
    return result[0]

def generic_create(key, data):
    table, pk, cols=TABLES[key]; allowed={k:v for k,v in data.items() if k in cols and v is not None}; names=list(allowed); placeholders=','.join(['%s']*len(names))
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(f'INSERT INTO {table} ({",".join(names)}) VALUES ({placeholders}) RETURNING *', tuple(allowed.values())); return rows(cur)[0]
    except Exception as exc: raise db_error(exc)

def generic_update(key, item_id, data):
    table, pk, cols=TABLES[key]; allowed={k:v for k,v in data.items() if k in cols and k not in (pk,) and v is not None}
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(f'UPDATE {table} SET ' + ','.join(f'{k}=%s' for k in allowed) + f' WHERE {pk}=%s RETURNING *', (*allowed.values(),item_id)); result=rows(cur)
    except Exception as exc: raise db_error(exc)
    if not result: raise HTTPException(404,'Record not found')
    return result[0]

app=FastAPI(title='InfraAssess API', version='6.0')
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.get('/api/health')
def health():
    postgres='ok'
    try:
        with connection() as conn: conn.execute('SELECT 1')
    except Exception: postgres='unavailable'
    vector='unconfigured'
    try:
        from vector_db.qdrant_store import IncidentStore
        from sentence_transformers import SentenceTransformer
        model=SentenceTransformer(settings.model_name); store=IncidentStore(settings.qdrant_path,settings.collection,int(model.get_sentence_embedding_dimension())); store.ensure_collection(); store.close(); vector='ok'
    except Exception:
        logger.exception('Vector-search health check failed for collection=%s path=%s', settings.collection, settings.qdrant_path)
        vector='unavailable'
    return {'api':'ok','postgres':postgres,'vector_search':vector}

@app.get('/api/dashboard')
def dashboard():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM component) components,(SELECT count(*) FROM incident WHERE status NOT IN ('RESOLVED','CLOSED')) open_incidents,(SELECT count(*) FROM work_order WHERE status NOT IN ('COMPLETED','CANCELLED')) active_work_orders,(SELECT count(*) FROM maintenance_alert WHERE status IN ('OPEN','ACKNOWLEDGED')) active_alerts"); return rows(cur)[0]

def install_crud(key, model):
    @app.get('/api/'+key)
    def listing(limit:int=Query(25,ge=1,le=100), offset:int=Query(0,ge=0), search:str|None=None, _key=key): return generic_list(_key,limit,offset,search)
    @app.get('/api/'+key+'/{item_id}')
    def getting(item_id:int, _key=key): return generic_get(_key,item_id)
    @app.post('/api/'+key, status_code=201)
    def creating(payload:model, _key=key): return generic_create(_key,payload.model_dump(exclude_none=True))
    @app.patch('/api/'+key+'/{item_id}')
    def updating(item_id:int,payload:model,_key=key): return generic_update(_key,item_id,payload.model_dump(exclude_none=True))
    @app.delete('/api/'+key+'/{item_id}', status_code=204)
    def deleting(item_id:int,_key=key):
        table,pk,_=TABLES[_key]
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute(f'DELETE FROM {table} WHERE {pk}=%s',(item_id,))
                if cur.rowcount==0: raise HTTPException(404,'Record not found')
        except HTTPException: raise
        except Exception as exc: raise db_error(exc)

for _key,_model in [('locations',dict),('categories',dict),('components',ComponentIn),('technicians',TechnicianIn),('assessments',AssessmentIn),('incidents',IncidentIn),('work-orders',WorkOrderIn),('maintenance-records',MaintenanceIn),('sensor-readings',SensorIn),('maintenance-alerts',AlertUpdate)]: install_crud(_key,_model)

@app.get('/api/audit-logs')
def audit(limit:int=Query(100,ge=1,le=500), offset:int=Query(0,ge=0)):
    with connection() as conn, conn.cursor() as cur: cur.execute('SELECT * FROM audit_log ORDER BY changed_at DESC LIMIT %s OFFSET %s',(limit,offset)); return rows(cur)

@app.post('/api/work-orders/{item_id}/complete')
def complete(item_id:int,payload:CompletionIn):
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute('SELECT work_order_number FROM work_order WHERE work_order_id=%s',(item_id,)); result=cur.fetchone()
            if not result: raise HTTPException(404,'Work order not found')
            cur.execute('CALL sp_complete_work_order(%s,%s,%s,%s,%s,%s,%s)',(result[0],payload.technician_id,payload.action_taken,payload.actual_cost,payload.outcome,payload.completed_at,payload.completion_notes))
        return generic_get('work-orders',item_id)
    except HTTPException: raise
    except Exception as exc: raise db_error(exc)

@app.get('/api/search/incidents')
def semantic_search(query:str=Query(...,min_length=1),limit:int=Query(5,ge=1,le=100)):
    try:
        from vector_db.embeddings import SentenceTransformerProvider
        from vector_db.qdrant_store import IncidentStore
        from vector_db.search import search_incidents
        provider=SentenceTransformerProvider(settings.model_name); store=IncidentStore(settings.qdrant_path,settings.collection,provider.dimension)
        try:
            with connection() as conn: return search_incidents(conn,store,provider,query,limit)
        finally: store.close()
    except HTTPException: raise
    except Exception as exc:
        logger.exception('Semantic incident search failed for collection=%s path=%s query_length=%d', settings.collection, settings.qdrant_path, len(query))
        raise HTTPException(503,'Semantic search is temporarily unavailable. Check the API logs for the underlying Qdrant, model or database error.') from exc
