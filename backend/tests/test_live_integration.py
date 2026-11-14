"""Live tests: only run against an explicitly supplied disposable installed database."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import psycopg
import pytest
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.auth import actor

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL must name a disposable database')

@pytest.fixture
def live(monkeypatch):
    conn = psycopg.connect(URL)
    @contextmanager
    def connection():
        with conn.transaction():
            conn.execute("SELECT set_config('app.user', %s, true)", (actor.get(),))
            yield conn
    # Outer transaction never commits test records.
    conn.execute('BEGIN')
    monkeypatch.setattr(main, 'connection', connection)
    client = TestClient(main.app, headers={'Authorization':'Bearer test-admin'})
    try: yield client, conn
    finally: conn.rollback(); conn.close()


def test_seed_backfill_and_historical_health(live):
    _, conn = live
    pump = conn.execute("SELECT component_id FROM component WHERE asset_tag='AST-PU-001'").fetchone()[0]
    assert conn.execute("SELECT count(*) FROM maintenance_alert WHERE component_id=%s AND alert_type='CRITICAL_HEALTH' AND status='OPEN'", (pump,)).fetchone()[0] == 1
    tech = conn.execute('SELECT technician_id FROM technician LIMIT 1').fetchone()[0]
    conn.execute("INSERT INTO assessment(component_id,technician_id,assessed_at,health_score,condition_status,findings) VALUES(%s,%s,clock_timestamp(),95,'GOOD','recovered')", (pump,tech))
    conn.execute("UPDATE assessment SET health_score=20 WHERE component_id=%s AND assessed_at<'2026-01-01'", (pump,))
    assert conn.execute("SELECT count(*) FROM maintenance_alert WHERE component_id=%s AND alert_type='CRITICAL_HEALTH' AND status IN ('OPEN','ACKNOWLEDGED')",(pump,)).fetchone()[0] == 0


def test_lifecycle_linking_deletes_and_actor(live):
    api, conn = live
    payload={'incident_number':'LIVE-'+uuid.uuid4().hex[:12], 'reported_at':'2026-01-01T00:00:00Z','severity':'HIGH','title':'Live incident','description':'Pump leakage'}
    result=api.post('/api/incidents',json=payload); assert result.status_code==201, result.text
    ident=result.json()['incident_id']
    assert api.patch(f'/api/incidents/{ident}',json={'status':'RESOLVED'}).status_code==422
    assert api.patch(f'/api/incidents/{ident}',json={'status':'RESOLVED','resolved_at':'2026-01-02T00:00:00Z'}).status_code==200
    component=conn.execute('SELECT component_id FROM component LIMIT 1').fetchone()[0]
    assert api.put(f'/api/incidents/{ident}/components/{component}',json={'impact_type':'PRIMARY'}).status_code==200
    assert api.get(f'/api/incidents/{ident}/components').json()[0]['component_id']==component
    assert api.delete(f'/api/incidents/{ident}').status_code==409
    assert api.delete(f'/api/incidents/{ident}/components/{component}').status_code==204
    assert api.delete(f'/api/incidents/{ident}').status_code==204
    audit=conn.execute("SELECT old_values, changed_by FROM audit_log WHERE entity_type='incident' AND entity_id=%s AND action='DELETE'",(ident,)).fetchone()
    assert audit[0]['incident_number']==payload['incident_number'] and audit[1]=='test-admin'


def test_completion_guards_and_rollback(live):
    api,conn=live
    component,tech=conn.execute('SELECT component_id,technician_id FROM component CROSS JOIN technician LIMIT 1').fetchone()
    result=api.post('/api/work-orders',json={'work_order_number':'LIVE-'+uuid.uuid4().hex[:12],'component_id':component,'technician_id':tech,'work_type':'PREVENTIVE','planned_start':'2026-01-01'})
    assert result.status_code==201,result.text
    ident=result.json()['work_order_id']
    completion={'technician_id':tech,'action_taken':'Repair','actual_cost':'123.45','outcome':'SUCCESSFUL','completed_at':'2026-11-14T00:00:00Z','completion_notes':'Verified'}
    assert api.post(f'/api/work-orders/{ident}/complete',json={**completion,'actual_cost':'-1'}).status_code==422
    assert conn.execute('SELECT count(*) FROM maintenance_record WHERE work_order_id=%s',(ident,)).fetchone()[0]==0
    conn.execute('UPDATE technician SET active=false WHERE technician_id=%s',(tech,))
    assert api.post(f'/api/work-orders/{ident}/complete',json=completion).status_code==422
    conn.execute('UPDATE technician SET active=true WHERE technician_id=%s',(tech,))
    assert api.post(f'/api/work-orders/{ident}/complete',json=completion).status_code==200
    assert api.post(f'/api/work-orders/{ident}/complete',json=completion).status_code==409
    assert api.patch(f'/api/work-orders/{ident}',json={'estimated_cost':'999.99'}).status_code==409
    assert conn.execute('SELECT count(*) FROM maintenance_record WHERE work_order_id=%s',(ident,)).fetchone()[0]==1
    maintenance_id=conn.execute('SELECT maintenance_id FROM maintenance_record WHERE work_order_id=%s',(ident,)).fetchone()[0]
    assert api.delete(f'/api/maintenance-records/{maintenance_id}').status_code==409


def test_sensor_recovery_reports_filters_and_injection(live):
    api,conn=live
    component=conn.execute('SELECT component_id FROM component LIMIT 1').fetchone()[0]
    threshold=api.post('/api/sensor-thresholds',json={'component_id':component,'sensor_type':'TEST','unit':'C','max_value':'50.00'})
    assert threshold.status_code==201,threshold.text
    result=api.post('/api/sensor-readings',json={'component_id':component,'sensor_type':'TEST','unit':'C','reading_value':'60.1234','recorded_at':'2026-01-01T00:00:00Z'})
    assert result.status_code==201,result.text
    assert conn.execute("SELECT count(*) FROM maintenance_alert WHERE component_id=%s AND alert_type='SENSOR_ANOMALY' AND status='OPEN'",(component,)).fetchone()[0]==1
    assert api.patch('/api/sensor-readings/'+str(result.json()['reading_id']),json={'reading_value':'40.0000'}).status_code==200
    assert conn.execute("SELECT count(*) FROM maintenance_alert WHERE component_id=%s AND alert_type='SENSOR_ANOMALY' AND status='OPEN'",(component,)).fetchone()[0]==0
    for report in ['health','failures','overdue']: assert api.get('/api/reports/'+report).status_code==200
    result=api.get('/api/incidents',params={'page':'true','severity':'HIGH','limit':2})
    assert result.status_code==200,result.text
    assert result.json()['total']>=len(result.json()['items'])
    assert all(x['severity']=='HIGH' for x in result.json()['items'])
    assert api.get('/api/incidents',params={'page':'true','sort':'incident_id; DROP TABLE incident'}).status_code==422
    assert api.get('/api/incidents',params={'page':'true','search':"'; DROP TABLE incident; --"}).json()['items']==[]


def test_true_concurrent_completion():
    number='RACE-'+uuid.uuid4().hex[:12]
    with psycopg.connect(URL) as conn:
        component,tech=conn.execute('SELECT component_id,technician_id FROM component CROSS JOIN technician LIMIT 1').fetchone()
        ident=conn.execute("INSERT INTO work_order(work_order_number,component_id,technician_id,work_type,planned_start) VALUES(%s,%s,%s,'PREVENTIVE','2026-01-01') RETURNING work_order_id",(number,component,tech)).fetchone()[0]
    def complete():
        try:
            with psycopg.connect(URL) as conn:
                conn.execute("SET statement_timeout='10s'")
                conn.execute("CALL sp_complete_work_order(%s,%s,'Concurrent test',1,'SUCCESSFUL',clock_timestamp(),'Verified')",(number,tech))
            return 'completed'
        except psycopg.errors.ObjectNotInPrerequisiteState: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(lambda _:complete(),range(2)))
    assert sorted(outcomes)==['completed','conflict']
    with psycopg.connect(URL) as conn:
        assert conn.execute('SELECT count(*) FROM maintenance_record WHERE work_order_id=%s',(ident,)).fetchone()[0]==1


@pytest.mark.parametrize('resource', ['locations','categories','components','technicians','assessments','incidents','work-orders','maintenance-records','sensor-readings','sensor-thresholds'])
def test_every_resource_live_crud(live, resource):
    api,conn=live
    suffix=uuid.uuid4().hex[:10]
    component,tech=conn.execute('SELECT component_id,technician_id FROM component CROSS JOIN technician LIMIT 1').fetchone()
    location,category=conn.execute('SELECT location_id,category_id FROM location CROSS JOIN component_category LIMIT 1').fetchone()
    order=conn.execute("INSERT INTO work_order(work_order_number,component_id,work_type,planned_start) VALUES(%s,%s,'PREVENTIVE','2026-01-01') RETURNING work_order_id",('CRUD-'+suffix,component)).fetchone()[0]
    cases={
      'locations':({'location_code':suffix,'name':'Test','address':'Test address','region':'North'},'name','Updated'),
      'categories':({'category_code':suffix,'name':suffix},'description','Updated'),
      'components':({'asset_tag':suffix,'name':'Test','location_id':location,'category_id':category},'name','Updated'),
      'technicians':({'employee_code':suffix,'full_name':'Test','email':suffix+'@example.org','specialty':'Mechanical'},'full_name','Updated'),
      'assessments':({'component_id':component,'technician_id':tech,'assessed_at':'2026-01-01T00:00:00Z','health_score':95,'condition_status':'GOOD','findings':'Test'},'findings','Updated'),
      'incidents':({'incident_number':suffix,'reported_at':'2026-01-01T00:00:00Z','severity':'LOW','title':'Test','description':'Test'},'title','Updated'),
      'work-orders':({'work_order_number':suffix,'component_id':component,'work_type':'PREVENTIVE','planned_start':'2026-01-01'},'estimated_cost','12.34'),
      'maintenance-records':({'work_order_id':order,'technician_id':tech,'performed_at':'2026-01-01T00:00:00Z','action_taken':'Test','actual_cost':'12.34','outcome':'SUCCESSFUL'},'action_taken','Updated'),
      'sensor-readings':({'component_id':component,'recorded_at':'2026-01-01T00:00:00Z','sensor_type':suffix,'reading_value':'12.3456','unit':'C'},'reading_value','22.3456'),
      'sensor-thresholds':({'component_id':component,'sensor_type':suffix,'unit':'C','max_value':'20.00'},'max_value','25.00'),
    }
    body,field,value=cases[resource]
    created=api.post('/api/'+resource,json=body)
    assert created.status_code==201,created.text
    pk=main.TABLES[resource][1];ident=created.json()[pk]
    assert api.get(f'/api/{resource}/{ident}').status_code==200
    assert api.patch(f'/api/{resource}/{ident}',json={field:value}).status_code==200
    assert api.delete(f'/api/{resource}/{ident}').status_code==204
    assert api.get(f'/api/{resource}/{ident}').status_code==404
    table=main.TABLES[resource][0]
    assert conn.execute("SELECT count(*) FROM audit_log WHERE entity_type=%s AND entity_id=%s AND action='DELETE' AND changed_by='test-admin'",(table,ident)).fetchone()[0]==1


def test_incident_creation_links_atomically(live):
    api,conn=live
    component=conn.execute('SELECT component_id FROM component LIMIT 1').fetchone()[0]
    number='ATOMIC-'+uuid.uuid4().hex[:10]
    body={'incident_number':number,'reported_at':'2026-01-01T00:00:00Z','severity':'LOW','title':'Test','description':'Test','component_ids':[component,9223372036854775807]}
    assert api.post('/api/incidents',json=body).status_code==409
    assert conn.execute('SELECT count(*) FROM incident WHERE incident_number=%s',(number,)).fetchone()[0]==0
    body['component_ids']=[component]
    created=api.post('/api/incidents',json=body)
    assert created.status_code==201,created.text
    assert api.get('/api/incidents/'+str(created.json()['incident_id'])+'/components').json()[0]['component_id']==component
