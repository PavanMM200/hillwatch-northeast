import json,uuid
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock
import numpy as np,pytest,rasterio,httpx
from rasterio.transform import from_origin
from app.config import Settings,settings
from app.errors import ServiceError
from app.geo import validate_line,corridor_segments,overlap
from app.routing import compute_routes
from app.schemas import RouteRequest
from app.gee import select_pair,validate_raster,initialize,download
from app.road_status import road_status
from app.matlab_adapter import validate_outputs,run

LINE={'type':'LineString','coordinates':[[93.60,27.08],[93.65,27.10]]}
NOW=datetime.now(timezone.utc)
def report():return {'client_id':str(uuid.uuid4()),'kind':'BLOCKAGE','latitude':27.09,'longitude':93.62,'observed_at':NOW.isoformat(),'description':'SIMULATED test report, no real incident.'}
def scene(date,**kwargs):return {'acquired_at':date,'coverage':.95,'orbit':'ASCENDING','relative_orbit':12,'polarizations':['VV','VH'],**kwargs}
def raster(path,count=2,epsg=32646,shift=0,fill=1):
    with rasterio.open(path,'w',driver='GTiff',height=20,width=20,count=count,dtype='float32',crs=f'EPSG:{epsg}',transform=from_origin(500000+shift,3000000,10,10)) as dst:dst.write(np.full((count,20,20),fill,dtype='float32'))

@pytest.mark.parametrize('project',['Bad_Project','x','123456','with spaces'])
def test_invalid_project(project):
    with pytest.raises(ValueError):Settings(ee_project=project,_env_file=None)
def test_not_configured(client):
    r=client.get('/api/integrations/status');assert r.status_code==200
    assert r.json()['maps_routes']['status']=='NOT CONFIGURED'
    r=client.post('/api/routes/compute',json={'origin':'Itanagar','destination':'Ziro'});assert r.status_code==503
    assert r.json()['code']=='MAPS_NOT_CONFIGURED'
def test_missing_auth(monkeypatch):
    monkeypatch.setattr(settings,'ee_project','')
    with pytest.raises(ServiceError,match='EE_PROJECT'):initialize()
@pytest.mark.parametrize('geometry',[{}, {'type':'Polygon','coordinates':[]},{'type':'LineString','coordinates':[[93,27],[93,27]]},{'type':'LineString','coordinates':[[float('nan'),27],[93,28]]},{'type':'LineString','coordinates':[[10,10],[11,11]]}])
def test_invalid_geometry(geometry):
    with pytest.raises(ServiceError):validate_line(geometry)
def test_corridor_order_and_units():
    corridor,segments=corridor_segments(LINE,300)
    assert corridor['type']=='Polygon' and len(segments)>1
    assert segments[0]['start_m']==0
    assert all(a['end_m']==b['start_m'] for a,b in zip(segments,segments[1:]))
    assert 4000<segments[-1]['end_m']<7000
def test_route_alternatives(monkeypatch):
    monkeypatch.setattr(settings,'maps_routes_key','simulated-key')
    response=Mock(status_code=200);response.json.return_value={'routes':[{'polyline':{'geoJsonLinestring':LINE},'distanceMeters':5000,'duration':'600s'}]*2}
    monkeypatch.setattr('app.routing.httpx.post',lambda *a,**kw:response)
    assert len(compute_routes(RouteRequest(origin='origin',destination='destination')))==2
@pytest.mark.parametrize('status',[400,403,429,500])
def test_route_provider_errors(monkeypatch,status):
    monkeypatch.setattr(settings,'maps_routes_key','simulated-secret-key')
    monkeypatch.setattr('app.routing.httpx.post',lambda *a,**kw:Mock(status_code=status))
    with pytest.raises(ServiceError) as error:compute_routes(RouteRequest(origin='origin',destination='destination'))
    assert 'simulated-secret-key' not in str(error.value)
def test_location_invalid(client):assert client.post('/api/routes/compute',json={'origin':' ','destination':'Ziro'}).status_code==422
def test_pair_selection():
    pair=select_pair([scene('2026-10-01'),scene('2026-10-10',relative_orbit=33),scene('2026-10-20')],True)
    assert pair[0]['acquired_at']=='2026-10-01' and pair[1]['acquired_at']=='2026-10-20'
@pytest.mark.parametrize('records',[[],[scene('2026-10-01')],[scene('2026-10-01',polarizations=['VV']),scene('2026-10-20')],[scene('2026-10-01',coverage=.1),scene('2026-10-20')]])
def test_unsuitable_sar(records):assert select_pair(records,True) is None
def test_cloud_obscured_pair():assert select_pair([scene('2026-10-01',coverage=0),scene('2026-10-20')]) is None
def test_valid_raster(tmp_path):
    p=tmp_path/'r.tif';raster(p);arr,valid,ref=validate_raster(p,2,32646);assert valid.all() and arr.shape==(2,20,20)
@pytest.mark.parametrize('count,epsg,fill',[(1,32646,1),(2,32645,1),(2,32646,-9999),(2,32646,float('nan'))])
def test_invalid_rasters(tmp_path,count,epsg,fill):
    p=tmp_path/'r.tif';raster(p,count,epsg,fill=fill)
    with pytest.raises(ServiceError):validate_raster(p,2,32646)
def test_missing_raster(tmp_path):
    with pytest.raises(ServiceError):validate_raster(tmp_path/'missing.tif',2)
def test_grid_mismatch(tmp_path):
    a=tmp_path/'a.tif';b=tmp_path/'b.tif';raster(a);raster(b,shift=10);_,_,ref=validate_raster(a,2)
    with pytest.raises(ServiceError):validate_raster(b,2,reference=ref)
def test_export_failure(monkeypatch,tmp_path):
    img=Mock();img.select.return_value.clip.return_value.unmask.return_value.toFloat.return_value.getDownloadURL.side_effect=RuntimeError('SIMULATED permission failure')
    monkeypatch.setattr('app.gee.time.sleep',lambda _:None)
    with pytest.raises(ServiceError,match='3 attempts'):download(img,None,{'epsg':32646,'transform':[10,0,0,0,-10,0],'width':10,'height':10},tmp_path/'x.tif',['VV','VH'],lambda:None)
def test_missing_matlab(monkeypatch,tmp_path):
    monkeypatch.setattr(settings,'matlab_executable','')
    with pytest.raises(ServiceError,match='MATLAB_EXECUTABLE'):run(tmp_path,lambda:None)
def test_output_missing(tmp_path):
    with pytest.raises(ServiceError):validate_outputs(tmp_path,{'id':'simulated','epsg':32646},{})
def test_valid_output_contract(tmp_path):
    raster(tmp_path/'sar_before.tif')
    raster(tmp_path/'change_mask.tif',count=1,fill=0)
    raster(tmp_path/'valid_mask.tif',count=1,fill=1)
    from PIL import Image
    Image.new('L',(20,20)).save(tmp_path/'sar_change.png')
    (tmp_path/'results.json').write_text(json.dumps({'algorithm':'experimental-sar-ndvi-v1','segment_id':'simulated','valid_fraction':.95}))
    result,features=validate_outputs(tmp_path,{'id':'simulated','epsg':32646,'geometry':LINE,'corridor_m':100},
        {'algorithm':'experimental-sar-ndvi-v1','scenes':[],'warnings':['SIMULATED']})
    assert features==[] and result['valid_fraction']==.95
def status(**kw):
    defaults={'candidates':[],'coverage_ok':True,'observations':[NOW.isoformat()],'at':NOW};defaults.update(kw);return road_status(**defaults)
@pytest.mark.parametrize('impact,expected',[(False,'LANDSLIDE CANDIDATE NEAR ROAD'),(True,'POSSIBLE LANDSLIDE WITH POTENTIAL ROAD IMPACT')])
def test_candidate_status(impact,expected):assert status(candidates=[{'properties':{'potential_road_impact':impact}}])['status']==expected
def test_no_change_not_clear():
    result=status();assert result['status']=='NO SIGNIFICANT CHANGE DETECTED';assert not result['official_closure'];assert 'does not establish' in result['limitation']
def test_stale():assert status(observations=[(NOW-timedelta(days=60)).isoformat()])['status']=='INSUFFICIENT OR STALE EVIDENCE'
def test_insufficient():assert status(coverage_ok=False)['status']=='INSUFFICIENT OR STALE EVIDENCE'
def test_unverified():assert status(incidents=[{'kind':'BLOCKAGE','status':'ACTIVE','moderation':'UNVERIFIED','observed_at':NOW.isoformat()}])['status']=='REPORTED BLOCKAGE — UNVERIFIED'
def test_official_and_conflict():
    result=status(verified=[{'closure':True,'decision':'VERIFIED','expires_at':(NOW+timedelta(hours=1)).isoformat()}]);assert result['official_closure'] and result['conflicting_evidence']
def test_expired_official():assert not status(verified=[{'closure':True,'decision':'VERIFIED','expires_at':(NOW-timedelta(hours=1)).isoformat()}])['official_closure']
def test_overlap():
    polygon={'type':'Polygon','coordinates':[[[93.619,27.086],[93.621,27.086],[93.621,27.09],[93.619,27.09],[93.619,27.086]]]}
    result=overlap(polygon,LINE,300);assert result['area_m2']>0 and result['corridor_intersection_m2']>0
def test_incident_idempotency_and_duplicate(client):
    body=report();a=client.post('/api/incidents',json=body);assert a.status_code==201
    b=client.post('/api/incidents',json=body);assert a.json()['id']==b.json()['id']
    body['client_id']=str(uuid.uuid4());c=client.post('/api/incidents',json=body);assert c.json()['duplicate_of']==a.json()['id']
    assert a.json()['moderation']=='UNVERIFIED' and a.json()['submitted_at']!=a.json()['observed_at']
def test_unauthorized_review(client):
    i=client.post('/api/incidents',json=report()).json()
    assert client.post('/api/incidents/'+i['id']+'/verify',json={}).status_code in (401,422)
    assert client.get('/api/official/queue').status_code==401
def test_verification(authority):
    i=authority.post('/api/incidents',json=report()).json()
    body={'decision':'VERIFIED','notes':'SIMULATED authorized review','source':'SIMULATED source','observed_at':NOW.isoformat(),'expires_at':(NOW+timedelta(hours=1)).isoformat(),'closure':True}
    r=authority.post('/api/incidents/'+i['id']+'/verify',json=body);assert r.status_code==200 and r.json()['moderation']=='VERIFIED'
    assert len(authority.get('/api/official/audit').json()['items'])>=2
def test_malicious_upload(authority):
    i=authority.post('/api/incidents',json=report()).json()
    r=authority.post('/api/incidents/'+i['id']+'/photo',files={'file':('../../evil.html',b'<script>alert(1)</script>','image/jpeg')});assert r.status_code==422
def test_path_injection(client):
    assert client.get('/api/analyses/../../.env/artifacts').status_code==404
    assert client.post('/api/analyses',json={'route_id':'../../evil','start_date':'2026-10-01','end_date':'2026-10-20'}).status_code==422
def test_secret_leak(client,monkeypatch):
    monkeypatch.setattr(settings,'maps_routes_key','TOP_SECRET_SIMULATED')
    assert 'TOP_SECRET' not in client.get('/api/integrations/status').text
    assert 'TOP_SECRET' not in client.get('/api/public-config').text
def test_csrf(client):
    client.headers.pop('X-Requested-With');assert client.post('/api/incidents',json=report()).status_code==403
def test_bad_origin(client):assert client.post('/api/incidents',headers={'Origin':'https://evil.invalid'},json=report()).status_code==403
def test_future_observation(client):
    body=report();body['observed_at']=(NOW+timedelta(days=1)).isoformat();assert client.post('/api/incidents',json=body).status_code==422
