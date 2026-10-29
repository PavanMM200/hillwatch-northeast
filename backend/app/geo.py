import math
from shapely.geometry import shape, mapping
from shapely.ops import transform, substring
from pyproj import CRS, Transformer
from .errors import ServiceError

def validate_line(geometry):
    try:
        if geometry.get('type') != 'LineString': raise ValueError()
        coordinates = geometry['coordinates']
        if not 2 <= len(coordinates) <= 25000: raise ValueError()
        for p in coordinates:
            if len(p) != 2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p): raise ValueError()
            if not 88 <= p[0] <= 98 or not 24 <= p[1] <= 30: raise ValueError()
        line = shape(geometry)
        if not line.is_valid or line.length == 0: raise ValueError()
        return line
    except (TypeError, ValueError, KeyError):
        raise ServiceError('INVALID_GEOMETRY','Expected a finite, nonzero LineString within Northeast India (88–98°E, 24–30°N).',422)
def projectors(line):
    c = line.centroid
    crs = CRS.from_proj4(f'+proj=aeqd +lat_0={c.y} +lon_0={c.x} +datum=WGS84 +units=m')
    return crs, Transformer.from_crs(4326,crs,always_xy=True).transform, Transformer.from_crs(crs,4326,always_xy=True).transform
def corridor_segments(geometry, width, max_km=400):
    line=validate_line(geometry)
    crs, forward, inverse=projectors(line)
    metric=transform(forward,line)
    if metric.length > max_km*1000: raise ServiceError('ROUTE_TOO_LONG',f'Limit route length to {max_km:g} km.',422)
    segments=[]
    for i,start in enumerate(range(0,math.ceil(metric.length),2000)):
        end=min(start+2000,metric.length); sub=substring(metric,start,end)
        # Each export uses local UTM on a short segment, bounding download dimensions.
        geo=transform(inverse,sub); c=geo.centroid; epsg=32600+int((c.x+180)//6)+1
        segments.append({'ordinal':i,'start_m':start,'end_m':end,'geometry':mapping(geo),
            'corridor':mapping(transform(inverse,sub.buffer(width))), 'epsg':epsg,'corridor_m':width})
    return mapping(transform(inverse,metric.buffer(width))),segments
def overlap(candidate_geojson, route_geometry, width):
    line=validate_line(route_geometry); _,f,_=projectors(line)
    road=transform(f,line); candidate=transform(f,shape(candidate_geojson)); corridor=road.buffer(width)
    return {'area_m2':candidate.area,'distance_to_route_m':candidate.distance(road),
            'distance_to_corridor_m':candidate.distance(corridor),'corridor_intersection_m2':candidate.intersection(corridor).area,
            'potentially_affected_road_m':road.intersection(candidate).length,
            'potential_road_impact':candidate.intersects(road.buffer(10)),
            'road_width_assumption_m':20}
