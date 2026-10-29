# Scientific and operational limitations

- No trained/calibrated model, validated accuracy, live satellite feed or guaranteed detection. The algorithm is a configurable research heuristic derived from the supplied workflow.
- SAR backscatter can change with moisture, vegetation, geometry and terrain artifacts. GRD intensity is not interferometric coherence. Same relative orbit and pass reduce geometry mismatch but do not remove all effects.
- No full radiometric terrain normalization, layover model or shadow correction is implemented. Terrain >45° is excluded, reducing coverage and potentially missing important landslides.
- Earth Engine SCL masking is imperfect. Optical data can be absent; SAR-only candidates remain experimental. SAR and optical observations may bracket different periods. NDVI loss has many causes.
- Default thresholds and minimum areas are not calibrated for this region. Ground-truth evaluation, sensitivity analysis and validation across seasons/terrain remain required.
- Native satellite resolution and route-centerline accuracy cannot reliably establish physical road blockage. The 20 m road footprint is an explicit assumption. Potential road impact and actual road closure are separate.
- Image search is capped at 60 recent candidates per query, and each scene must cover at least 85% of the corridor. The implementation does not mosaic partial scenes. A route may have unavailable sections even when some imagery exists.
- Direct GeoTIFF exports run in a background worker with bounded requests. There is no GCS/Drive long-running export task integration. Long routes can still consume substantial API quota and processing time.
- API keys, identity permissions, billing and MATLAB licensing must be supplied and verified. A configured project ID is not a working Earth Engine session.
- MATLAB Production Server is not supported; batch and Engine are implemented. Docker does not bundle MATLAB. Actual end-to-end satellite-to-MATLAB acceptance depends on configured services.
- The initial SQLite option supports a single worker. PostgreSQL/PostGIS migration and container launch need verification on the deployment host. Shared/distributed rate limiting and scheduler supervision are deployment responsibilities.
- Role membership is locally provisioned, not an agency identity integration. No government organization is connected. Official source credibility must be checked by authorized reviewers.
- Public routes/jobs use unguessable UUIDs rather than private user ownership. This research design exposes analysis artifacts to anyone with their URLs. Public incident descriptions and coordinates must not contain personal data. Photos require sign-in and reviewer-only reading; production should add submitter ownership and consent/retention policies.
- Offline queued incident text is browser-local and may be lost if browser data is cleared. It is not submitted until acknowledged by the API. Offline photos are not queued. Cached results are explicitly historical; map tiles are not cached.
- No SMS, rainfall, weather, WhatsApp or external closure feed is fabricated or integrated. No emergency dispatch function is included.
- Acceptance is incomplete until real routing, authenticated scene search/download, licensed MATLAB outputs, reviewer operations and regional scientific validation have been exercised. Do not claim production readiness.
