import importlib.util, json, os, subprocess, time
from pathlib import Path
import numpy as np, rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer
from .config import settings, ROOT
from .errors import ServiceError
from .gee import validate_raster
from .geo import overlap

def quote(value): return str(value).replace("'","''")
def run(directory,check):
    manifest=directory/'input.json'
    code=f"addpath('{quote(ROOT/'matlab')}'); run_route_analysis('{quote(manifest.resolve())}');"
    if settings.matlab_method=='engine':
        # Execute engine in an isolated subprocess so cancellation/timeout apply.
        command=[__import__('sys').executable,'-m','app.matlab_engine_runner',str(manifest.resolve())]
    elif settings.matlab_method=='batch':
        if not settings.matlab_executable or not Path(settings.matlab_executable).is_file():
            raise ServiceError('MATLAB_NOT_CONFIGURED','Set MATLAB_EXECUTABLE to a licensed MATLAB installation.')
        command=[settings.matlab_executable,'-batch',code]
    else: raise ServiceError('MATLAB_METHOD','Only batch and Engine are implemented. MATLAB Runtime alone is unsupported.')
    prefs=settings.matlab_work_dir/'preferences';prefs.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'MATLAB_PREFDIR':str(prefs.resolve())}
    with (directory/'processing.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=directory,stdout=log,stderr=subprocess.STDOUT,env=env)
        started=time.monotonic()
        try:
            while process.poll() is None:
                check()
                if time.monotonic()-started>settings.matlab_timeout_seconds: raise ServiceError('MATLAB_TIMEOUT','MATLAB exceeded configured execution timeout.')
                time.sleep(.5)
            if process.returncode: raise ServiceError('MATLAB_FAILED','MATLAB failed. Inspect the local processing.log for licensing, toolbox or input errors.')
        finally:
            if process.poll() is None:
                if os.name=='nt': subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                else: process.kill()
                process.wait(timeout=30)

def validate_outputs(directory,segment,manifest):
    try:
        result=json.loads((directory/'results.json').read_text())
        if result['algorithm']!='experimental-sar-ndvi-v1' or result['segment_id']!=segment['id']: raise ValueError()
        _,_,ref=validate_raster(directory/'sar_before.tif',2,segment['epsg'])
        arr,valid,_=validate_raster(directory/'change_mask.tif',1,segment['epsg'],ref)
        values=set(np.unique(arr[0][valid]).tolist())
        if not values <= {0,1}: raise ValueError()
        coverage=result['valid_fraction']
        if not isinstance(coverage,(float,int)) or not 0<=coverage<=1: raise ValueError()
        required=['sar_change.png','results.json','change_mask.tif','valid_mask.tif']
        for name in required:
            if not (directory/name).is_file(): raise ValueError()
        from PIL import Image
        with Image.open(directory/'sar_change.png') as preview:
            preview.verify()
        validity,_,_=validate_raster(directory/'valid_mask.tif',1,segment['epsg'],ref)
        if not set(np.unique(validity).tolist()) <= {0,1}: raise ValueError()
        if np.any((arr[0]==1)&(validity[0]!=1)): raise ValueError()
        with rasterio.open(directory/'change_mask.tif') as src:
            mask=src.read(1);to_geo=Transformer.from_crs(src.crs,4326,always_xy=True).transform
            features=[]
            for geom,value in shapes(mask.astype('uint8'),mask=mask==1,transform=src.transform):
                if value!=1: continue
                geometry=mapping(transform(to_geo,shape(geom)))
                props=overlap(geometry,segment['geometry'],segment['corridor_m'])
                from .terrain_impact import assess
                props['terrain_impact']=assess(directory,geometry)
                props['potential_road_impact']=props['terrain_impact']['direct_overlap'] or props['terrain_impact']['paths_reaching_road']>0
                props.update({'segment_id':segment['id'],'algorithm':manifest['algorithm'],'acquisitions':manifest['scenes'],
                    'verification':'UNVERIFIED','quality_limitations':manifest['warnings']})
                features.append({'type':'Feature','geometry':geometry,'properties':props})
        collection={'type':'FeatureCollection','features':features}
        (directory/'candidates.geojson').write_text(json.dumps(collection),encoding='utf-8')
        return result,features
    except ServiceError: raise
    except Exception: raise ServiceError('MATLAB_OUTPUT_INVALID','MATLAB outputs failed schema, raster or georeferencing validation.')
