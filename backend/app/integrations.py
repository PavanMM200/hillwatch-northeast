import importlib.util,json,subprocess,os,tempfile
from pathlib import Path
from .config import settings
from .database import now

def status():
    p=settings.data_dir/'integration_checks.json'
    saved=json.loads(p.read_text()) if p.exists() else {}
    # Never equate presence of a key with a successful request.
    configured={'maps_routes':True,'maps_browser':True,
                'earth_engine':bool(settings.ee_project),'matlab':bool(settings.matlab_executable) or settings.matlab_method=='engine'}
    return {key:{'configured':value,'status':saved.get(key,{}).get('status','NOT VERIFIED' if value else 'NOT CONFIGURED'),
        'checked_at':saved.get(key,{}).get('checked_at'),'message':saved.get(key,{}).get('message','Run scripts/check_integrations.py; configuration alone does not prove access.')} for key,value in configured.items()}

def verify():
    from .gee import initialize
    from .routing import compute_routes
    from .schemas import RouteRequest
    from .errors import ServiceError
    results={}
    for name,configured,fn in [
        ('earth_engine',bool(settings.ee_project),lambda:initialize().Number(1).getInfo()),
        ('maps_routes',True,lambda:compute_routes(RouteRequest(origin='Itanagar, Arunachal Pradesh',destination='Naharlagun, Arunachal Pradesh'))),
        ('matlab',bool(settings.matlab_executable) or settings.matlab_method=='engine',verify_matlab)]:
        try:
            if not configured: results[name]={'status':'NOT CONFIGURED','message':'Use scripts/setup_wizard.py.'}
            else: fn();results[name]={'status':'PASS','message':'Actual service check succeeded.'}
        except Exception as e:
            results[name]={'status':'FAIL','message':e.message if isinstance(e,ServiceError) else f'{type(e).__name__}: check authentication, permissions or local service logs.'}
        results[name]['checked_at']=now()
    results['maps_browser']={'status':'NO KEY REQUIRED',
         'message':'Leaflet satellite map needs internet access. Open Plan a journey to view the map.','checked_at':now()}
    (settings.data_dir/'integration_checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    return results

def verify_matlab():
    from .errors import ServiceError
    code="assert(license('test','image_toolbox') && license('test','map_toolbox')); disp(version);"
    if settings.matlab_method=='engine':
        import matlab.engine
        engine=matlab.engine.start_matlab()
        try: engine.eval(code,nargout=0)
        finally: engine.quit()
    else:
        if not Path(settings.matlab_executable).is_file(): raise ServiceError('MATLAB_PATH','Configured MATLAB executable does not exist.')
        prefs=settings.matlab_work_dir/'preferences';prefs.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([settings.matlab_executable,'-batch',code],capture_output=True,text=True,timeout=180,
           env={**os.environ,'MATLAB_PREFDIR':str(prefs.resolve())})
        (settings.data_dir/'matlab-check.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode: raise ServiceError('MATLAB_FAILED','MATLAB startup/toolbox check failed; inspect data/matlab-check.log.')
