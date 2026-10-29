"""Durable database queue. Run exactly one worker with SQLite; PostgreSQL supports SKIP LOCKED."""
import json, shutil, time
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from shapely.geometry import Point, shape
from .database import Session, Job, Route, Segment, Scene, Candidate, Incident, Evidence, now
from .config import settings
from .errors import ServiceError
from .gee import prepare_segment
from .matlab_adapter import run, validate_outputs
from .road_status import road_status

def corroborate(db,segment):
    reports=[];verified=[];area=shape(segment['corridor'])
    for i in db.scalars(select(Incident).where(Incident.status=='ACTIVE',Incident.moderation!='REJECTED')):
        if area.covers(Point(i.longitude,i.latitude)):
            reports.append({'id':i.id,'kind':i.kind,'status':i.status,'moderation':i.moderation,'observed_at':i.observed_at})
            # Latest decision supersedes any older closure decision.
            e=db.scalar(select(Evidence).where(Evidence.incident_id==i.id).order_by(Evidence.created_at.desc()).limit(1))
            if e: verified.append({**e.payload,'incident_id':i.id,'verified_at':e.created_at})
    return reports,verified

def execute(job_id):
    directory=(settings.data_dir/'jobs'/job_id).resolve();directory.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    def check():
        with Session() as db:
            job=db.get(Job,job_id)
            if job.state in ('cancel_requested','cancelled'): raise ServiceError('CANCELLED','Analysis cancelled.')
            if time.monotonic()-started>settings.job_timeout_seconds: raise ServiceError('JOB_TIMEOUT','Analysis exceeded total time limit.')
            job.updated_at=now();db.commit()
    try:
        with Session() as db:
            job=db.get(Job,job_id); request=job.request
            segments=[{**s.payload,'id':s.id} for s in db.scalars(select(Segment).where(Segment.route_id==job.route_id).order_by(Segment.ordinal))]
        results=[];all_features=[]
        for index,segment in enumerate(segments):
            check();work=directory/segment['id']
            try:
                manifest=prepare_segment(segment,request,work,check)
                with Session() as db:
                    for scene in manifest['scenes']: db.add(Scene(job_id=job_id,payload={**scene,'segment_id':segment['id']}))
                    db.commit()
                run(work,check);check()
                statistics,features=validate_outputs(work,segment,manifest)
                observations=[s['acquired_at'] for s in manifest['scenes'] if s['collection']=='COPERNICUS/S1_GRD']
                # Freshness is judged on the newest observation; baseline age remains visible separately.
                with Session() as db:
                    reports,verified=corroborate(db,segment)
                    state=road_status(candidates=features,coverage_ok=statistics['valid_fraction']>=settings.min_coverage,
                       observations=[max(observations)],incidents=reports,verified=verified,stale_days=settings.stale_days)
                    for feature in features: db.add(Candidate(job_id=job_id,segment_id=segment['id'],payload=feature))
                    db.commit()
                results.append({'segment':segment,'statistics':statistics,'scenes':manifest['scenes'],'warnings':manifest['warnings'],
                                'road_status':state,'candidates':features,'reports':reports})
                all_features.extend(features)
            except ServiceError as exc:
                if exc.code in ('CANCELLED','JOB_TIMEOUT','MATLAB_NOT_CONFIGURED','MATLAB_FAILED','EE_NOT_CONFIGURED','EE_AUTH'): raise
                shutil.rmtree(work,ignore_errors=True)
                results.append({'segment':segment,'error':{'code':exc.code,'message':exc.message},
                    'road_status':road_status(candidates=[],coverage_ok=False,observations=[]),'warnings':[exc.message]})
            with Session() as db:
                job=db.get(Job,job_id);job.progress=round((index+1)/len(segments)*95);job.result={'segments':results};job.updated_at=now();db.commit()
        check()
        (directory/'candidates.geojson').write_text(json.dumps({'type':'FeatureCollection','features':all_features}),encoding='utf-8')
        with Session() as db:
            job=db.get(Job,job_id);job.state='completed' if all('error' not in r for r in results) else 'partial'
            job.progress=100;job.updated_at=now();job.result={'segments':results,'processed_at':now(),'algorithm':'experimental-sar-ndvi-v1'};db.commit()
        (directory/'results.json').write_text(json.dumps(job.result,indent=2),encoding='utf-8')
    except Exception as exc:
        code=exc.code if isinstance(exc,ServiceError) else 'PROCESSING_ERROR'
        message=exc.message if isinstance(exc,ServiceError) else 'Processing failed; inspect server environment. Provider details suppressed to protect credentials.'
        with Session() as db:
            job=db.get(Job,job_id);job.state='cancelled' if code=='CANCELLED' else 'failed';job.error=f'{code}: {message}';job.updated_at=now();db.commit()
        # Retain only local processing logs for diagnosing failed MATLAB launches.
        for p in directory.rglob('*'):
            if p.is_file() and p.name!='processing.log': p.unlink()

def worker():
    while True:
        with Session() as db:
            # Interrupted jobs must never remain falsely running after worker death.
            cutoff=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
            db.execute(update(Job).where(Job.state.in_(['running','cancel_requested']),Job.updated_at<cutoff).values(state='failed',error='WORKER_INTERRUPTED: retry with a new job.'))
            job=db.scalar(select(Job).where(Job.state=='queued').order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))
            job_id=job.id if job else None
            if job: job.state='running';job.updated_at=now()
            db.commit()
        if job_id: execute(job_id)
        else: time.sleep(2)
if __name__=='__main__': worker()
