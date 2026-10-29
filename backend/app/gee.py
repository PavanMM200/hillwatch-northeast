"""Bounded, same-grid exports derived from the supplied Colab pipeline.

No authentication prompt is opened in a web request. No synthetic fallback.
"""
import json, math, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx, numpy as np, rasterio
from rasterio.transform import from_origin
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer
from PIL import Image
from .config import settings
from .errors import ServiceError

def initialize():
    if not settings.ee_project: raise ServiceError('EE_NOT_CONFIGURED','Set EE_PROJECT and authenticate with the terminal wizard.')
    import ee
    try:
        if settings.ee_auth_method == 'local':
            credentials=ee.data.get_persistent_credentials()
        elif settings.ee_auth_method == 'service_account':
            if not settings.ee_service_account or not settings.google_application_credentials:
                raise ServiceError('EE_CREDENTIALS','Service account identity and credentials path are required.')
            credentials=ee.ServiceAccountCredentials(settings.ee_service_account,settings.google_application_credentials)
        elif settings.ee_auth_method == 'adc':
            import google.auth
            credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/earthengine','https://www.googleapis.com/auth/cloud-platform'])
        else: raise ServiceError('EE_AUTH_METHOD','Use adc, local or service_account authentication.')
        ee.Initialize(credentials=credentials,project=settings.ee_project)
        ee.data.setDeadline(120000)
        return ee
    except ServiceError: raise
    except Exception: raise ServiceError('EE_AUTH','Earth Engine authentication/initialization failed. Check credentials, API enablement, project registration and permissions.')

def select_pair(records, sar=False):
    """Newest suitable pair; SAR must share pass, relative orbit and dual bands."""
    records=sorted(records,key=lambda r:r['acquired_at'],reverse=True)
    for i,after in enumerate(records):
        for before in records[i+1:]:
            if before['acquired_at'][:10] == after['acquired_at'][:10]: continue
            if sar and (before.get('relative_orbit')!=after.get('relative_orbit') or before.get('orbit')!=after.get('orbit')): continue
            if sar and any(not {'VV','VH'} <= set(r.get('polarizations',[])) for r in (before,after)): continue
            if min(before['coverage'],after['coverage']) < settings.min_coverage: continue
            return [before,after]
    return None

def optical_mask(ee,image):
    scl=image.select('SCL')
    # Reject no-data, saturated, dark/shadow, clouds, cirrus and snow. Keep vegetation/bare/water.
    valid=scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6))
    return image.select(['B4','B3','B2','B8']).updateMask(valid)

def search(ee,region,start,end,sar):
    collection='COPERNICUS/S1_GRD' if sar else 'COPERNICUS/S2_SR_HARMONIZED'
    coll=ee.ImageCollection(collection).filterBounds(region).filterDate(start,end)
    if sar:
        coll=coll.filter(ee.Filter.eq('instrumentMode','IW')).filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV')).filter(ee.Filter.listContains('transmitterReceiverPolarisation','VH'))
    else: coll=coll.filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE',80))
    coll=coll.sort('system:time_start',False).limit(settings.scene_limit)
    def annotate(img):
        valid=img.select(['VV','VH']).mask().reduce(ee.Reducer.min()) if sar else optical_mask(ee,img).mask().reduce(ee.Reducer.min())
        # Unmask beyond footprint so partial scenes cannot masquerade as full coverage.
        coverage=valid.unmask(0,False).reduceRegion(ee.Reducer.mean(),region,60,maxPixels=2000000).values().get(0)
        return img.set('route_coverage',coverage)
    info=coll.map(annotate).getInfo()
    records=[]
    for f in info.get('features',[]):
        p=f['properties']; bands=f.get('bands',[])
        records.append({'scene_id':f['id'],'collection':collection,
          'acquired_at':datetime.fromtimestamp(p['system:time_start']/1000,timezone.utc).isoformat(),
          'coverage':float(p.get('route_coverage') or 0),'orbit':p.get('orbitProperties_pass'),
          'relative_orbit':p.get('relativeOrbitNumber_start'),'polarizations':p.get('transmitterReceiverPolarisation',[]),
          'cloud_percent':p.get('CLOUDY_PIXEL_PERCENTAGE'),'native_projection':bands[0].get('crs') if bands else None,
          'bands':['VV','VH'] if sar else ['B4','B3','B2','B8'], 'units':'dB' if sar else 'reflectance_scaled_10000',
          'nominal_resolution_m':10})
    return records

def validate_raster(path, count, expected_crs=None, reference=None):
    try:
        with rasterio.open(path) as src:
            if src.count != count or not src.crs or src.width*src.height>2000000: raise ValueError('bands, CRS or size')
            if expected_crs and src.crs.to_epsg()!=expected_crs: raise ValueError('projection')
            if reference and (src.shape!=reference[0] or src.transform!=reference[1] or src.crs!=reference[2]): raise ValueError('grid mismatch')
            arr=src.read().astype('float32'); valid=np.all(np.isfinite(arr)&(arr!=-9999),axis=0)
            if not valid.any(): raise ValueError('all pixels invalid')
            return arr,valid,(src.shape,src.transform,src.crs)
    except Exception as exc: raise ServiceError('INVALID_RASTER',f'Raster validation failed ({type(exc).__name__}); no analysis published.')

def download(image,region,grid,path,bands,check):
    for attempt in range(3):
        check()
        try:
            url=image.select(bands).clip(region).unmask(-9999).toFloat().getDownloadURL({
              'format':'GEO_TIFF','crs':f"EPSG:{grid['epsg']}",
              'crs_transform':grid['transform'],'dimensions':[grid['width'],grid['height']]})
            size=0
            with httpx.stream('GET',url,timeout=120,follow_redirects=True) as response:
                response.raise_for_status()
                with path.with_suffix('.part').open('wb') as out:
                    for chunk in response.iter_bytes(65536):
                        check();size+=len(chunk)
                        if size>32*1024*1024: raise ServiceError('EXPORT_TOO_LARGE','Segment download exceeded 32 MiB.')
                        out.write(chunk)
            path.with_suffix('.part').replace(path)
            validate_raster(path,len(bands),grid['epsg'])
            return
        except ServiceError: raise
        except Exception:
            path.with_suffix('.part').unlink(missing_ok=True)
            if attempt==2: raise ServiceError('EE_EXPORT','Earth Engine download failed after 3 attempts. Check quota, permission and network; no output fabricated.')
            time.sleep(2**attempt)

def prepare_segment(segment,request,directory,check):
    ee=initialize(); check(); directory.mkdir(parents=True,exist_ok=True)
    region=ee.Geometry(segment['corridor']); scenes=[]; warnings=[]; pairs={}
    for sensor,sar in [('sar',True),('optical',False)]:
        records=search(ee,region,request['start_date'],request['end_date'],sar);check()
        pair=select_pair(records,sar)
        if not pair and request['fallback_days']:
            earlier=(datetime.fromisoformat(request['start_date'])-timedelta(days=request['fallback_days'])).date().isoformat()
            records=search(ee,region,earlier,request['end_date'],sar); pair=select_pair(records,sar)
            warnings.append(f'{sensor}: expanded search to {earlier}; actual acquisition dates retained.')
        if pair: pairs[sensor]=pair;scenes.extend(pair)
        else: warnings.append(f'{sensor}: no suitable pair among the newest {settings.scene_limit} scenes in the configured search period.')
    if 'sar' not in pairs: raise ServiceError('NO_SAR_PAIR','No same-orbit, dual-polarization SAR pair with sufficient corridor coverage. Try a longer date interval.')
    f=Transformer.from_crs(4326,segment['epsg'],always_xy=True).transform
    bounds=transform(f,shape(segment['corridor'])).bounds
    xmin,ymin,xmax,ymax=bounds; xmin=math.floor(xmin/10)*10; ymax=math.ceil(ymax/10)*10
    width=math.ceil((xmax-xmin)/10);height=math.ceil((ymax-ymin)/10)
    grid={'epsg':segment['epsg'],'transform':[10,0,xmin,0,-10,ymax],'width':width,'height':height}
    if width*height*4*4>30*1024*1024: raise ServiceError('EXPORT_TOO_LARGE','Segment bounds exceed safe direct-download size.')
    files={};reference=None
    for sensor,pair in pairs.items():
        for phase,scene in zip(['before','after'],pair):
            check();img=ee.Image(scene['scene_id'])
            if sensor=='optical': img=optical_mask(ee,img)
            path=directory/f'{sensor}_{phase}.tif'
            download(img,region,grid,path,scene['bands'],check)
            arr,valid,ref=validate_raster(path,len(scene['bands']),segment['epsg'],reference)
            reference=ref;files[f'{sensor}_{phase}']=str(path.resolve())
            scene['export_projection']=f"EPSG:{segment['epsg']}";scene['export_resolution_m']=10
            display=np.where(np.isfinite(arr)&(arr!=-9999),arr,0)
            rgb=np.stack([np.clip((display[0]+25)/25,0,1),np.clip((display[1]+30)/25,0,1),np.clip((display[0]-display[1])/15,0,1)],-1) if sensor=='sar' else np.moveaxis(np.clip(display[:3]/3000,0,1),0,-1)**.8
            rgb[~valid]=0;Image.fromarray((rgb*255).astype('uint8')).save(directory/f'{sensor}_{phase}.png')
    dem=ee.Image('USGS/SRTMGL1_003');terrain=ee.Terrain.products(dem)
    download(terrain,region,grid,directory/'terrain.tif',['elevation','slope','hillshade'],check)
    files['terrain']=str((directory/'terrain.tif').resolve())
    arr,_,_=validate_raster(directory/'terrain.tif',3,segment['epsg'],reference)
    Image.fromarray(np.clip(arr[2],0,255).astype('uint8')).save(directory/'hillshade.png')
    affine=from_origin(xmin,ymax,10,10)
    road=transform(f,shape(segment['geometry']))
    masks={'road':road.buffer(10),'corridor':transform(f,shape(segment['corridor']))}
    for name,geom in masks.items():
        path=directory/f'{name}.tif'
        with rasterio.open(path,'w',driver='GTiff',height=height,width=width,count=1,dtype='uint8',crs=f"EPSG:{segment['epsg']}",transform=affine) as dst:
            dst.write(rasterize([(geom,1)],out_shape=(height,width),transform=affine,all_touched=True),1)
        files[name]=str(path.resolve())
    warnings+=['SAR shadow and layover are not fully corrected; steep-slope masking cannot eliminate terrain artifacts.',
               'SRTM is static historical elevation (~February 2000); 30 m native data resampled to the 10 m analysis grid.',
               '20 m road-width assumption and satellite pixel size limit physical obstruction inference.']
    manifest={'files':files,'scenes':scenes,'sar_units':'dB','sar_bands':['VV','VH'],'optical_bands':['B4','B3','B2','B8'],
       'epsg':segment['epsg'],'nodata':-9999,'threshold_db':settings.sar_threshold_db,'ndvi_loss':settings.ndvi_loss_threshold,
       'min_pixels':settings.min_candidate_pixels,'min_slope':settings.min_slope_degrees,
       'min_coverage':settings.min_coverage,'output_dir':str(directory.resolve()),'warnings':warnings,
       'algorithm':'experimental-sar-ndvi-v1','segment_id':segment['id']}
    (directory/'input.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest
