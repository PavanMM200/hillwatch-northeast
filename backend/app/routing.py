import httpx
from .errors import ServiceError
from .geo import corridor_segments
from .config import settings

def waypoint(text):
    try:
        parts=[float(x.strip()) for x in text.split(',')]
        if len(parts)==2:
            lat,lon=parts
            if not 24<=lat<=30 or not 88<=lon<=98: raise ServiceError('INVALID_LOCATION','Coordinates must be within Northeast India.',422)
            return {'location':{'latLng':{'latitude':lat,'longitude':lon}}}
    except ValueError: pass
    return {'address':text}
def google_routes(request):
    if not settings.maps_routes_key: raise ServiceError('MAPS_NOT_CONFIGURED','Configure MAPS_ROUTES_KEY using the terminal wizard.')
    try:
        response=httpx.post('https://routes.googleapis.com/directions/v2:computeRoutes', timeout=30,
          headers={'X-Goog-Api-Key':settings.maps_routes_key,'X-Goog-FieldMask':'routes.distanceMeters,routes.duration,routes.polyline.geoJsonLinestring,routes.description'},
          json={'origin':waypoint(request.origin),'destination':waypoint(request.destination),'travelMode':'DRIVE',
                'computeAlternativeRoutes':True,'polylineEncoding':'GEO_JSON_LINESTRING','polylineQuality':'HIGH_QUALITY'})
    except httpx.RequestError: raise ServiceError('MAPS_NETWORK','Routes API could not be reached. Retry later.')
    if response.status_code != 200: raise ServiceError('MAPS_PROVIDER',f'Routes API returned HTTP {response.status_code}. Check billing, API enablement and server key restrictions.')
    try:
        routes=response.json().get('routes',[])
        if not routes: raise ServiceError('NO_ROUTE','Google returned no driving route.',422)
        output=[]
        for r in routes:
            geometry=r['polyline']['geoJsonLinestring']
            corridor,segments=corridor_segments(geometry,request.corridor_m,settings.max_route_km)
            output.append({'origin':request.origin,'destination':request.destination,'geometry':geometry,'corridor':corridor,
                'corridor_m':request.corridor_m,'distance_m':r['distanceMeters'],'duration':r['duration'],
                'description':r.get('description','Driving route'),'segments':segments,'source':'Google Maps Routes API'})
        return output
    except (KeyError,TypeError,ValueError): raise ServiceError('MAPS_RESPONSE','Routes API returned an invalid response.')

import time, threading
from functools import lru_cache
_lock=threading.Lock()
_last=0.0
@lru_cache(maxsize=256)
def resolve_location(text):
    global _last
    point=waypoint(text)
    if 'location' in point:
        p=point['location']['latLng'];return p['longitude'],p['latitude']
    with _lock:
        time.sleep(max(0,1.1-(time.monotonic()-_last)))
        try:
            r=httpx.get('https://nominatim.openstreetmap.org/search',params={'q':text,'format':'json','countrycodes':'in','viewbox':'88,30,98,24','bounded':1,'limit':1},headers={'User-Agent':'Hillwatch-NIT-Arunachal-Research/1.0'},timeout=30)
            r.raise_for_status();items=r.json()
        finally: _last=time.monotonic()
    if not items: raise ServiceError('LOCATION_NOT_FOUND','Place not found. Click the map or enter latitude,longitude.',422)
    return float(items[0]['lon']),float(items[0]['lat'])

def compute_routes(request):
    try:
        a,b=resolve_location(request.origin),resolve_location(request.destination)
        r=httpx.get(f'https://router.project-osrm.org/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}',params={'overview':'full','geometries':'geojson','alternatives':'true'},timeout=60)
        r.raise_for_status();data=r.json()
        if data.get('code')!='Ok' or not data.get('routes'): raise ServiceError('NO_ROUTE','No driving route found.',422)
        output=[]
        for item in data['routes']:
            geometry=item['geometry'];corridor,segments=corridor_segments(geometry,request.corridor_m,settings.max_route_km)
            output.append(dict(origin=request.origin,destination=request.destination,geometry=geometry,corridor=corridor,corridor_m=request.corridor_m,distance_m=item['distance'],duration=str(item['duration'])+'s',description='OpenStreetMap driving route',segments=segments,source='OSRM / OpenStreetMap'))
        return output
    except httpx.HTTPError: raise ServiceError('ROUTING_UNAVAILABLE','Free routing or place search is temporarily unavailable. Please retry.')
