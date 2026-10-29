# Earth Engine

The user supplied project ID `ananya-499117`. It is stored only in the local `.env`; templates do not invent a project. Project IDs are not API keys, but access still requires authenticated credentials and an authorized registered project.

Enable Earth Engine API, register the Cloud project for Earth Engine use, and grant the selected identity the required access. Choose one method in the wizard:

- `local`: run `earthengine authenticate` or choose the wizard's authentication prompt. Backend reads persistent Earth Engine credentials; it never starts an interactive login in a request.
- `adc`: run `gcloud auth application-default login`, or use an appropriate workload identity on the deployment host. The backend obtains Application Default Credentials.
- `service_account`: provide the authorized identity and a local credentials path. Prefer a managed server identity for production. Never commit JSON keys or send them to the website.

Run `python scripts/check_integrations.py` to initialize the actual project and evaluate a trivial server-side value. PASS here proves basic access, not successful satellite processing.

## Collections and selection

- `COPERNICUS/S1_GRD`: IW mode, both VV and VH, same pass and relative orbit. Values are already dB; MATLAB does not convert them twice.
- `COPERNICUS/S2_SR_HARMONIZED`: B4,B3,B2,B8; SCL classes 4,5,6 retained, rejecting cloud/shadow/snow/no-data. NDVI uses scaled reflectance with valid denominator checks.
- `USGS/SRTMGL1_003`: historical elevation. Terrain slope and hillshade are derived at the native source before export; native 30 m terrain is resampled to the 10 m grid and not claimed as native 10 m elevation.

Search the requested half-open interval first. If no usable pair exists, search the explicitly configured number of earlier days. Choose the latest compatible pair with different acquisition days and minimum 85% valid corridor coverage by default. Search is capped at the newest 60 scenes per sensor/section; a missing pair is an explicit limitation. Coverage is measured across the whole AOI with masked/outside-footprint cells counted invalid.

Exports are bounded direct GeoTIFF downloads orchestrated asynchronously by the worker, not Earth Engine Drive export tasks. Common UTM grids, approximately 2 km section lengths, 32 MiB transfer caps, timeouts, validation, retry and cancellation prevent unbounded route downloads. Cancellation is checked between network calls/chunks; an in-flight Earth Engine metadata call can take up to its deadline.

No SAR pair stops that section. Missing optical data allows SAR-only experimental candidates with a warning. Actual acquisition dates and scene identifiers are always retained. SAR and optical acquisition times may differ; their corroboration is not proof that they observed the same event.

References:
- https://developers.google.com/earth-engine/guides/auth
- https://developers.google.com/earth-engine/guides/sentinel1
- https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl
- https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
- https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003
