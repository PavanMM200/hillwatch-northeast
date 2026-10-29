import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, mapping
from shapely.ops import transform
from pyproj import Transformer
from app.terrain_impact import assess

def test_downhill_connectivity_and_disconnected_road(tmp_path):
    grid=from_origin(500000,3000000,10,10)
    dem=np.tile(np.arange(9,0,-1,dtype='float32'),(9,1))
    road=np.zeros((9,9),dtype='float32');road[:,7]=1
    def write(name,data):
        with rasterio.open(tmp_path/name,'w',driver='GTiff',height=9,width=9,count=1,dtype='float32',crs='EPSG:32646',transform=grid) as dst: dst.write(data,1)
    write('terrain.tif',dem);write('road.tif',road)
    geo=mapping(transform(Transformer.from_crs(32646,4326,always_xy=True).transform,box(500010,2999950,500030,2999970)))
    result=assess(tmp_path,geo)
    assert result['paths_reaching_road']>0
    assert not result['direct_overlap']
    assert result['blockage_confirmed'] is False
    write('terrain.tif',-dem)
    assert assess(tmp_path,geo)['paths_reaching_road']==0
    road[:]=1;write('road.tif',road)
    assert assess(tmp_path,geo)['direct_overlap']
