import hashlib, io, json, secrets, time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, UploadFile, File, Query
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from PIL import Image, UnidentifiedImageError
from .database import Session, Base, engine, User, LoginSession, Route, Segment, Job, Incident, Evidence, Audit, now
from .config import settings
from .schemas import RouteRequest, AnalysisRequest, IncidentRequest, Verification, IncidentStatus, Login
from .errors import ServiceError
from .auth import current_user,roles,check_password,new_session,hash_password
from .routing import compute_routes
from .integrations import status
from .geo import projectors
from shapely.geometry import Point
from shapely.ops import transform

@asynccontextmanager
async def lifespan(app):
    yield
app=FastAPI(title='Hillwatch Northeast',version='0.1.0',lifespan=lifespan,description='Experimental terrain-change evidence and reviewed road reports. Never a road-safety guarantee.')
origins=settings.allowed_origins.split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type','X-Requested-With'])
limits=defaultdict(deque)

@app.middleware('http')
async def guard(request,call_next):
    origin=request.headers.get('origin')
    if request.method in ('POST','PATCH','DELETE'):
        if origin and origin not in origins: return JSONResponse({'code':'ORIGIN','message':'Origin is not allowed.'},403)
        if request.headers.get('x-requested-with')!='Hillwatch': return JSONResponse({'code':'CSRF','message':'X-Requested-With: Hillwatch required.'},403)
        total=0;chunks=[]
        async for chunk in request.stream():
            total+=len(chunk)
            if total>6*1024*1024:return JSONResponse({'code':'SIZE','message':'Request exceeds 6 MiB.'},413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    if request.url.path not in ('/api/health','/api/public-config'):
        key=(request.client.host if request.client else 'unknown', 'login' if request.url.path.endswith('/login') else 'api')
        t=time.monotonic();q=limits[key]
        while q and q[0]<t-60:q.popleft()
        if len(q)>=(8 if key[1]=='login' else 120): return JSONResponse({'code':'RATE_LIMIT','message':'Please retry in one minute.'},429)
        q.append(t)
        if len(limits)>10000:
            for k in list(limits):
                if not limits[k] or limits[k][-1]<t-60:del limits[k]
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(ServiceError)
async def service_error(request,exc): return JSONResponse({'code':exc.code,'message':exc.message},exc.status)
@app.exception_handler(Exception)
async def unexpected(request,exc): return JSONResponse({'code':'INTERNAL','message':'Request failed. Check local server configuration; no provider secrets are returned.'},500)
def get(db,model,id):
    row=db.get(model,str(id))
    if not row: raise ServiceError('NOT_FOUND','Record not found.',404)
    return row
def record(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns}
def incident_view(i):
    data=record(i);data.pop('client_id');data.pop('photo');data['has_photo']=bool(i.photo)
    data['stale']=datetime.now(timezone.utc)-datetime.fromisoformat(i.observed_at)>timedelta(days=settings.stale_days)
    return data
def audit(db,user,action,target,payload=None):db.add(Audit(actor=user.id,action=action,target=str(target),payload=payload or {}))

@app.get('/api/health')
def health():return {'status':'ok','time':now(),'mode':'REAL','scientific_validation':'experimental'}
@app.get('/api/public-config')
def public_config():return {'maps_browser_key':settings.maps_browser_key,'project_name':'Hillwatch Northeast'}
@app.get('/api/integrations/status')
def integration_status():return status()
@app.post('/api/auth/login')
def login(body:Login,response:Response):
    with Session() as db:
        user=db.scalar(select(User).where(User.username==body.username))
        # Match password work even for unknown users.
        valid=check_password(body.password,user.password_hash if user else hash_password('invalid',salt='00'*16))
        if not user or not valid:raise ServiceError('LOGIN','Invalid username or password.',401)
        token=new_session(db,user);audit(db,user,'login',user.id);db.commit()
        response.set_cookie('hill_session',token,httponly=True,secure=settings.cookie_secure,samesite='strict',max_age=28800,path='/')
        return {'username':user.username,'role':user.role}
@app.get('/api/auth/me')
def me(user=Depends(current_user)):return {'username':user.username,'role':user.role}
@app.post('/api/auth/logout')
def logout(request:Request,response:Response):
    with Session() as db:
        token=request.cookies.get('hill_session','');s=db.get(LoginSession,hashlib.sha256(token.encode()).hexdigest())
        if s:db.delete(s);db.commit()
    response.delete_cookie('hill_session');return {'signed_out':True}
@app.post('/api/routes/compute')
def routes(body:RouteRequest):
    output=[]
    for payload in compute_routes(body):
        with Session() as db:
            route=Route(payload={k:v for k,v in payload.items() if k!='segments'});db.add(route);db.flush()
            segments=[]
            for item in payload['segments']:
                s=Segment(route_id=route.id,ordinal=item['ordinal'],payload=item);db.add(s);db.flush();segments.append({**item,'id':s.id})
            db.commit();output.append({**route.payload,'id':route.id,'segments':segments,'created_at':route.created_at})
    return {'routes':output}
@app.post('/api/analyses',status_code=202)
def start_analysis(body:AnalysisRequest):
    # Require server-stored provider route; client cannot substitute geometry or paths.
    with Session() as db:
        route=get(db,Route,body.route_id)
        if datetime.now(timezone.utc)-datetime.fromisoformat(route.created_at)>timedelta(days=1):raise ServiceError('STALE_ROUTE','Recompute route before starting analysis.',409)
        if db.scalar(select(func.count()).select_from(Job).where(Job.state.in_(['queued','running'])))>=20:raise ServiceError('QUEUE_FULL','Analysis queue is full. Retry later.',429)
        job=Job(route_id=route.id,request=body.model_dump(mode='json'));db.add(job);db.commit();return record(job)
@app.get('/api/analyses/{analysis_id}')
def analysis(analysis_id:UUID):
    with Session() as db:return record(get(db,Job,analysis_id))
@app.post('/api/analyses/{analysis_id}/cancel')
def cancel(analysis_id:UUID):
    with Session() as db:
        job=get(db,Job,analysis_id)
        if job.state=='queued':job.state='cancelled'
        elif job.state=='running':job.state='cancel_requested'
        db.commit();return {'state':job.state}
@app.get('/api/analyses/{analysis_id}/results')
def results(analysis_id:UUID):
    from .jobs import corroborate
    from .road_status import road_status
    with Session() as db:
        job=get(db,Job,analysis_id)
        if job.state not in ('completed','partial'):raise ServiceError('NOT_READY','Validated results are not available.',409)
        result=json.loads(json.dumps(job.result))
        for s in result['segments']:
            reports,verified=corroborate(db,s['segment'])
            dates=[x['acquired_at'] for x in s.get('scenes',[]) if x['collection']=='COPERNICUS/S1_GRD']
            s['road_status']=road_status(candidates=s.get('candidates',[]),coverage_ok=s.get('statistics',{}).get('valid_fraction',0)>=settings.min_coverage,
                observations=[max(dates)] if dates else [],incidents=reports,verified=verified,stale_days=settings.stale_days)
        result['status_evaluated_at']=now();return result

def artifact_paths(job_id):
    root=(settings.data_dir/'jobs'/str(job_id)).resolve()
    allowed={'.json','.geojson','.tif','.png'}
    return [(p.relative_to(root).as_posix(),p) for p in root.rglob('*') if p.is_file() and p.suffix in allowed and p.name!='input.json']
@app.get('/api/analyses/{analysis_id}/artifacts')
def artifacts(analysis_id:UUID):
    with Session() as db:
        job=get(db,Job,analysis_id)
        if job.state not in ('completed','partial'):return {'artifacts':[]}
    return {'artifacts':[{'id':hashlib.sha256(name.encode()).hexdigest()[:24],'name':name,'bytes':p.stat().st_size,
       'url':f'/api/analyses/{analysis_id}/artifacts/{hashlib.sha256(name.encode()).hexdigest()[:24]}'} for name,p in artifact_paths(analysis_id)]}
@app.get('/api/analyses/{analysis_id}/artifacts/{artifact_id}')
def artifact(analysis_id:UUID,artifact_id:str):
    permitted=artifacts(analysis_id)['artifacts']
    name=next((a['name'] for a in permitted if a['id']==artifact_id),None)
    if not name:raise ServiceError('NOT_FOUND','Artifact not found.',404)
    path=dict(artifact_paths(analysis_id))[name]
    return FileResponse(path,filename=path.name)

@app.get('/api/analyses/{analysis_id}/terrain/{segment_id}')
def terrain_preview(analysis_id:UUID,segment_id:UUID,whole:bool=False):
    import numpy as np, rasterio
    from rasterio.enums import Resampling
    with Session() as db:
        job=get(db,Job,analysis_id)
        if job.state not in ('completed','partial'): raise ServiceError('NOT_READY','Analysis not complete.',409)
        if not any(s['segment']['id']==str(segment_id) for s in job.result['segments']): raise ServiceError('NOT_FOUND','Section not found.',404)
    directory=settings.data_dir/'jobs'/str(analysis_id)/str(segment_id)
    if whole:
        from rasterio.merge import merge
        from contextlib import ExitStack
        paths=list((settings.data_dir/'jobs'/str(analysis_id)).glob('*/terrain.tif'))
        if not paths: raise ServiceError('NOT_FOUND','Terrain unavailable.',404)
        with ExitStack() as stack:
            sources=[stack.enter_context(rasterio.open(p)) for p in paths]
            if len({s.crs.to_string() for s in sources})!=1: raise ServiceError('TERRAIN_CRS','Whole-route preview requires matching projections.',422)
            left=min(s.bounds.left for s in sources);right=max(s.bounds.right for s in sources)
            bottom=min(s.bounds.bottom for s in sources);top=max(s.bounds.top for s in sources)
            resolution=max(right-left,top-bottom)/150
            z,_=merge(sources,bounds=(left,bottom,right,top),res=resolution,indexes=[1],nodata=-9999)
            masks={}
            for name in ('road','change_mask'):
                inputs=[stack.enter_context(rasterio.open(p.parent/(name+'.tif'))) for p in paths]
                mask,_=merge(inputs,bounds=(left,bottom,right,top),res=resolution,indexes=[1],nodata=0,method='max')
                masks[name]=mask[0].tolist()
        return dict(elevation=np.where(np.isfinite(z[0])&(z[0]!=-9999),z[0],None).tolist(),width_m=right-left,height_m=top-bottom,**masks)
    if not (directory/'terrain.tif').exists(): raise ServiceError('NOT_FOUND','Terrain unavailable.',404)
    with rasterio.open(directory/'terrain.tif') as src:
        h=max(2,round(src.height/max(src.height,src.width)*90));w=max(2,round(src.width/max(src.height,src.width)*90))
        z=src.read(1,out_shape=(h,w),resampling=Resampling.nearest)
        width=src.bounds.right-src.bounds.left;height=src.bounds.top-src.bounds.bottom
    masks={}
    for name in ('road','change_mask'):
        with rasterio.open(directory/(name+'.tif')) as src: masks[name]=src.read(1,out_shape=(h,w),resampling=Resampling.nearest).tolist()
    return dict(elevation=np.where(np.isfinite(z)&(z!=-9999),z,None).tolist(),width_m=width,height_m=height,**masks)

@app.post('/api/incidents',status_code=201)
def submit(body:IncidentRequest):
    with Session() as db:
        prior=db.scalar(select(Incident).where(Incident.client_id==str(body.client_id)))
        if prior:return incident_view(prior)
        if body.route_id:get(db,Route,body.route_id)
        if body.segment_id:
            s=get(db,Segment,body.segment_id)
            if body.route_id and s.route_id!=str(body.route_id):raise ServiceError('SEGMENT','Segment does not belong to route.',422)
        payload=body.model_dump(mode='json');i=Incident(**payload)
        # Approximate duplicate prefilter, then geodesic distance, same type/time.
        from pyproj import Geod
        geod=Geod(ellps='WGS84')
        for prior in db.scalars(select(Incident).where(Incident.kind==body.kind,Incident.latitude.between(body.latitude-.01,body.latitude+.01),Incident.longitude.between(body.longitude-.01,body.longitude+.01))):
            distance=geod.inv(body.longitude,body.latitude,prior.longitude,prior.latitude)[2]
            if distance<100 and abs((datetime.fromisoformat(prior.observed_at)-body.observed_at).total_seconds())<21600:i.duplicate_of=prior.id;break
        db.add(i);db.commit();return incident_view(i)
@app.get('/api/incidents')
def incidents(offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
    with Session() as db:return {'items':[incident_view(i) for i in db.scalars(select(Incident).where(Incident.moderation!='REJECTED').order_by(Incident.submitted_at.desc()).offset(offset).limit(limit))],'offset':offset,'limit':limit}
@app.get('/api/incidents/{incident_id}')
def incident(incident_id:UUID):
    with Session() as db:return incident_view(get(db,Incident,incident_id))
@app.post('/api/incidents/{incident_id}/flag')
def flag(incident_id:UUID):
    with Session() as db:
        i=get(db,Incident,incident_id);i.flags+=1;db.commit();return {'flagged':True}
@app.post('/api/incidents/{incident_id}/photo')
async def photo(incident_id:UUID,file:UploadFile=File(...),user=Depends(current_user)):
    content=await file.read(5*1024*1024+1)
    if len(content)>5*1024*1024:raise ServiceError('UPLOAD_SIZE','Photograph exceeds 5 MiB.',413)
    try:
        Image.MAX_IMAGE_PIXELS=20000000
        im=Image.open(io.BytesIO(content));im.verify()
        im=Image.open(io.BytesIO(content))
        if im.format not in ('JPEG','PNG'):raise ValueError()
        im=im.convert('RGB');im.thumbnail((2000,2000))
    except Exception:raise ServiceError('UPLOAD_INVALID','Upload a valid JPEG or PNG photograph under 20 megapixels.',422)
    with Session() as db:
        i=get(db,Incident,incident_id)
        if i.photo:raise ServiceError('PHOTO_EXISTS','A photograph is already attached.',409)
        path=settings.data_dir/'photos';path.mkdir(exist_ok=True);name=secrets.token_hex(24)+'.jpg';im.save(path/name,quality=85)
        i.photo=name;audit(db,user,'attach_photo',i.id);db.commit();return {'attached':True,'verification':'UNVERIFIED'}
@app.get('/api/official/incidents/{incident_id}/photo')
def view_photo(incident_id:UUID,user=Depends(roles('Reviewer','Road Authority','Administrator'))):
    with Session() as db:
        i=get(db,Incident,incident_id)
        if not i.photo:raise ServiceError('NOT_FOUND','No photograph.',404)
        return FileResponse(settings.data_dir/'photos'/i.photo,media_type='image/jpeg')
@app.post('/api/incidents/{incident_id}/verify')
def verify_incident(incident_id:UUID,body:Verification,user=Depends(roles('Reviewer','Road Authority','Administrator'))):
    if body.closure and user.role not in ('Road Authority','Administrator'):raise ServiceError('ROLE','Only Road Authority or Administrator can confirm a closure.',403)
    with Session() as db:
        i=get(db,Incident,incident_id);i.moderation=body.decision
        payload=body.model_dump(mode='json');db.add(Evidence(incident_id=i.id,reviewer_id=user.id,payload=payload));audit(db,user,'verify_incident',i.id,payload);db.commit();return incident_view(i)
@app.patch('/api/incidents/{incident_id}/status')
def update_status(incident_id:UUID,body:IncidentStatus,user=Depends(roles('Road Authority','Administrator'))):
    with Session() as db:
        i=get(db,Incident,incident_id);i.status=body.status;audit(db,user,'incident_status',i.id,body.model_dump());db.commit();return incident_view(i)
@app.get('/api/official/queue')
def queue(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user=Depends(roles('Reviewer','Road Authority','Administrator'))):
    with Session() as db:return {'items':[incident_view(i) for i in db.scalars(select(Incident).order_by(Incident.submitted_at.desc()).offset(offset).limit(limit))]}
@app.get('/api/official/audit')
def logs(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user=Depends(roles('Reviewer','Road Authority','Administrator'))):
    with Session() as db:return {'items':[record(a) for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).offset(offset).limit(limit))]}
@app.get('/api/official/export')
def export(user=Depends(roles('Reviewer','Road Authority','Administrator'))):
    with Session() as db:
        rows=[incident_view(i) for i in db.scalars(select(Incident).limit(10000))]
        audit(db,user,'export','incidents',{'count':len(rows)});db.commit()
    return Response(json.dumps({'exported_at':now(),'records':rows}),media_type='application/json',headers={'Content-Disposition':'attachment; filename=incident-records.json'})
