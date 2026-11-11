from contextlib import contextmanager
from functools import lru_cache
from threading import RLock
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg import Error as DatabaseError, OperationalError
from psycopg.errors import ForeignKeyViolation, UniqueViolation, CheckViolation, RestrictViolation, NotNullViolation, StringDataRightTruncation, ObjectNotInPrerequisiteState, RaiseException
from .config import FRONTEND_ORIGIN, settings
from .db import connection, rows
from .schemas import *

logger = logging.getLogger('infraassess.semantic_search')
vector_lock = RLock()

@lru_cache(maxsize=1)
def embedding_provider():
    from vector_db.embeddings import SentenceTransformerProvider
    return SentenceTransformerProvider(settings.model_name)

@contextmanager
def vector_store(dimension):
    from vector_db.qdrant_store import IncidentStore
    # Local Qdrant permits one client at a time, including concurrent requests.
    with vector_lock:
        store = IncidentStore(settings.qdrant_path, settings.collection, dimension)
        try:
            yield store
        finally:
            store.close()

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
    if isinstance(exc, (ForeignKeyViolation, RestrictViolation)): return HTTPException(409, 'A related record is missing, or this record is still in use.')
    if isinstance(exc, UniqueViolation): return HTTPException(409, 'A record with this unique identifier already exists.')
    if isinstance(exc, (CheckViolation, NotNullViolation, StringDataRightTruncation)): return HTTPException(422, 'The record violates a database integrity rule.')
    if isinstance(exc, ObjectNotInPrerequisiteState): return HTTPException(409, 'This work order is already completed or cancelled.')
    if isinstance(exc, RaiseException): return HTTPException(422, 'The operation violates a database workflow rule.')
    if isinstance(exc, OperationalError): return HTTPException(503, 'The database is temporarily unavailable.')
    logger.error('Database operation failed', exc_info=exc)
    return HTTPException(500, 'Database operation failed.')

def generic_list(key, limit, offset, search):
    table, pk, cols = TABLES[key]; where=''; params=[]
    if search:
        text_cols=[c for c in cols if c in ('name','title','description','asset_tag','incident_number','work_order_number','full_name','specialty','location_code','address','region','category_code','employee_code','email','findings','work_type','completion_notes','action_taken','outcome','sensor_type','unit','status','condition_status','alert_type','message')]
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
    if key == 'work-orders' and data.get('status') == 'COMPLETED':
        raise HTTPException(422, 'Create an open work order, then use the completion operation.')
    table, pk, cols=TABLES[key]; allowed={k:v for k,v in data.items() if k in cols and v is not None}; names=list(allowed); placeholders=','.join(['%s']*len(names))
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(f'INSERT INTO {table} ({",".join(names)}) VALUES ({placeholders}) RETURNING *', tuple(allowed.values())); return rows(cur)[0]
    except Exception as exc: raise db_error(exc)

def generic_update(key, item_id, data):
    table, pk, cols=TABLES[key]; allowed={k:v for k,v in data.items() if k in cols and k not in (pk,)}
    if not allowed: raise HTTPException(422, 'Provide at least one editable field.')
    try:
        with connection() as conn, conn.cursor() as cur:
            if key == 'work-orders' and 'status' in allowed:
                cur.execute('SELECT status FROM work_order WHERE work_order_id=%s FOR UPDATE', (item_id,))
                current = cur.fetchone()
                if not current: raise HTTPException(404, 'Record not found')
                if current[0] in ('COMPLETED', 'CANCELLED') and allowed['status'] != current[0]:
                    raise HTTPException(409, 'Completed or cancelled work orders cannot be reopened.')
                if allowed['status'] == 'COMPLETED' and current[0] != 'COMPLETED':
                    raise HTTPException(422, 'Use the work-order completion operation.')
            cur.execute(f'UPDATE {table} SET ' + ','.join(f'{k}=%s' for k in allowed) + f' WHERE {pk}=%s RETURNING *', (*allowed.values(),item_id)); result=rows(cur)
    except HTTPException: raise
    except Exception as exc: raise db_error(exc)
    if not result: raise HTTPException(404,'Record not found')
    return result[0]

app=FastAPI(title='InfraAssess API', version='6.0')
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.exception_handler(DatabaseError)
async def handle_database_error(request, exc):
    error = db_error(exc)
    return JSONResponse(status_code=error.status_code, content={'detail': error.detail})

@app.get('/api/health')
def health():
    postgres='ok'
    try:
        with connection() as conn: conn.execute('SELECT 1')
    except Exception: postgres='unavailable'
    vector='unconfigured'
    # A slow model/index operation must not block liveness probes.
    if not vector_lock.acquire(blocking=False):
        return {'api':'ok','postgres':postgres,'vector_search':'busy'}
    try:
        with vector_store(settings.dimension) as store:
            store.ensure_collection()
        vector='ok'
    except Exception:
        logger.exception('Vector-search health check failed for collection=%s path=%s', settings.collection, settings.qdrant_path)
        vector='unavailable'
    finally:
        vector_lock.release()
    return {'api':'ok','postgres':postgres,'vector_search':vector}

@app.get('/api/dashboard')
def dashboard():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM component) components,(SELECT count(*) FROM incident WHERE status NOT IN ('RESOLVED','CLOSED')) open_incidents,(SELECT count(*) FROM work_order WHERE status NOT IN ('COMPLETED','CANCELLED')) active_work_orders,(SELECT count(*) FROM maintenance_alert WHERE status IN ('OPEN','ACKNOWLEDGED')) active_alerts"); return rows(cur)[0]

def install_crud(key, model):
    update_model = patch_model(model)
    @app.get('/api/'+key)
    def listing(limit:int=Query(25,ge=1,le=100), offset:int=Query(0,ge=0), search:str|None=None): return generic_list(key,limit,offset,search)
    @app.get('/api/'+key+'/{item_id}')
    def getting(item_id:int): return generic_get(key,item_id)
    @app.post('/api/'+key, status_code=201)
    def creating(payload:model): return generic_create(key,payload.model_dump(exclude_none=True))
    @app.patch('/api/'+key+'/{item_id}')
    def updating(item_id:int,payload:update_model): return generic_update(key,item_id,payload.model_dump(exclude_unset=True))
    @app.delete('/api/'+key+'/{item_id}', status_code=204)
    def deleting(item_id:int):
        table,pk,_=TABLES[key]
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute(f'DELETE FROM {table} WHERE {pk}=%s',(item_id,))
                if cur.rowcount==0: raise HTTPException(404,'Record not found')
        except HTTPException: raise
        except Exception as exc: raise db_error(exc)

for _key,_model in [('locations',LocationIn),('categories',CategoryIn),('components',ComponentIn),('technicians',TechnicianIn),('assessments',AssessmentIn),('incidents',IncidentIn),('work-orders',WorkOrderIn),('maintenance-records',MaintenanceIn),('sensor-readings',SensorIn)]: install_crud(_key,_model)

# Alerts are produced by database workflows; operators may change their status.
@app.get('/api/maintenance-alerts')
def list_alerts(limit:int=Query(25,ge=1,le=100), offset:int=Query(0,ge=0), search:str|None=None):
    return generic_list('maintenance-alerts', limit, offset, search)

@app.get('/api/maintenance-alerts/{item_id}')
def get_alert(item_id:int): return generic_get('maintenance-alerts', item_id)

@app.patch('/api/maintenance-alerts/{item_id}')
def update_alert(item_id:int, payload:AlertUpdate):
    return generic_update('maintenance-alerts', item_id, payload.model_dump())

@app.get('/api/audit-logs')
def audit(limit:int=Query(100,ge=1,le=500), offset:int=Query(0,ge=0), search:str|None=None):
    with connection() as conn, conn.cursor() as cur:
        where = ''
        params = []
        if search:
            where = ' WHERE entity_type ILIKE %s OR action ILIKE %s OR changed_by ILIKE %s'
            params = ['%' + search + '%'] * 3
        cur.execute('SELECT * FROM audit_log' + where + ' ORDER BY changed_at DESC, audit_id DESC LIMIT %s OFFSET %s', (*params,limit,offset))
        return rows(cur)

@app.post('/api/work-orders/{item_id}/complete')
def complete(item_id:int,payload:CompletionIn):
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute('SELECT work_order_number FROM work_order WHERE work_order_id=%s FOR UPDATE',(item_id,)); result=cur.fetchone()
            if not result: raise HTTPException(404,'Work order not found')
            cur.execute('CALL sp_complete_work_order(%s,%s,%s,%s,%s,%s,%s)',(result[0],payload.technician_id,payload.action_taken,payload.actual_cost,payload.outcome,payload.completed_at,payload.completion_notes))
            cur.execute('SELECT * FROM work_order WHERE work_order_id=%s', (item_id,))
            return rows(cur)[0]
    except HTTPException: raise
    except Exception as exc: raise db_error(exc)

@app.get('/api/search/incidents')
def semantic_search(query:str=Query(...,min_length=1),limit:int=Query(5,ge=1,le=100)):
    query = ' '.join(query.split())
    if not query: raise HTTPException(422, 'Search query must not be blank.')
    try:
        from vector_db.indexer import index_incidents
        from vector_db.search import search_incidents
        with vector_lock:
            provider = embedding_provider()
            with vector_store(provider.dimension) as store, connection() as conn:
                index_incidents(conn, store, provider)
                return search_incidents(conn,store,provider,query,limit)
    except HTTPException: raise
    except Exception as exc:
        logger.exception('Semantic incident search failed for collection=%s path=%s query_length=%d', settings.collection, settings.qdrant_path, len(query))
        raise HTTPException(503,'Semantic search is temporarily unavailable. Check the API logs for the underlying Qdrant, model or database error.') from exc
