"""Screen downhill connectivity; not a debris-flow simulation or closure detector."""
import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer

def assess(directory, geometry):
    with rasterio.open(directory/'terrain.tif') as src:
        elevation=src.read(1)
        project=Transformer.from_crs(4326,src.crs,always_xy=True).transform
        source=rasterize([(mapping(transform(project,shape(geometry))),1)],out_shape=src.shape,transform=src.transform).astype(bool)
        pixel=float(abs(src.transform.a))
    with rasterio.open(directory/'road.tif') as src: road=src.read(1)>0
    valid=np.isfinite(elevation)&(elevation!=-9999)
    starts=np.argwhere(source&valid)
    direct=bool(np.any(source&road))
    reached=0; truncated=0; lengths=[]
    # Bounded sample keeps large scars tractable; every path must descend strictly.
    starts=starts[::max(1,int(np.ceil(len(starts)/200)))]
    for row,col in starts:
        length=0.0
        for step in range(200):
            if road[row,col]: reached+=1;lengths.append(length);break
            options=[]
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    rr,cc=row+dr,col+dc
                    if (dr or dc) and 0<=rr<elevation.shape[0] and 0<=cc<elevation.shape[1] and valid[rr,cc]:
                        distance=pixel*np.hypot(dr,dc)
                        drop=float(elevation[row,col]-elevation[rr,cc])
                        if drop>0: options.append((drop/distance,rr,cc,distance))
            if not options:
                if row in (0,elevation.shape[0]-1) or col in (0,elevation.shape[1]-1): truncated+=1
                break
            _,row,col,distance=max(options);length+=distance
        else: truncated+=1
    return {'assessment':'CHANGE OVERLAPS ROAD BUFFER' if direct else 'POSSIBLE DOWNHILL CONNECTION TO ROAD' if reached else 'NO DOWNHILL CONNECTION RESOLVED',
        'direct_overlap':direct,'paths_tested':len(starts),'paths_reaching_road':reached,
        'shortest_path_m':min(lengths) if lengths else None,'truncated_paths':truncated,
        'confidence':'LOW','blockage_confirmed':False,
        'limitation':'Screening only: steepest descent on resampled DEM, limited to extracted corridor. Road buffer is not measured road width. No debris volume, runout physics or passability estimate. Unresolved paths do not establish a clear road.'}
