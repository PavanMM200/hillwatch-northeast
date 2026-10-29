# Verification report — 29 October 2026 (Asia/Calcutta)

## Executed successfully

| Check | Result |
|---|---|
| React/TypeScript type check and Vite production build | PASS; 1,581 modules, approximately 262 kB JS before gzip |
| Python syntax compilation | PASS |
| Backend pytest suite | **53 passed**, 0 failed; 27 upstream deprecation warnings |
| MATLAB function tests | **9 passed**, 0 failed/incomplete, including full simulated GeoTIFF processing |
| SQLite migration | PASS; local schema initialized |
| FastAPI startup and browser integration-status requests | PASS |
| Desktop/mobile route-planner visual inspection | PASS for inspected layouts |
| Browser routing without key | Correct explicit configuration error; no fabricated route |
| Browser official workspace | Sign-in required |
| Earth Engine initialization/server computation | PASS with user-supplied project `ananya-499117` and existing local authentication |
| MATLAB startup and toolbox license checks | PASS, MATLAB R2025a Update 1; Image Processing and Mapping toolboxes |
| Real Sentinel-1, Sentinel-2 and SRTM export | PASS on a bounded test corridor |
| Real MATLAB batch adapter on exported satellite inputs | PASS |
| Georeferenced output, preview, and JSON validation | PASS after correcting and regression-testing mask indexing |

Tests use isolated simulated fixtures and a temporary SQLite database. No test incidents were inserted into the application database. MATLAB synthetic tests are not a scientific validation study.

## Real satellite integration exercise

The test used a short **synthetic test centerline, not a Google driving route**, from `[93.620,27.090]` to `[93.625,27.093]`, buffered by 100 m. It was kept outside the live database and public results. Search interval: 1 September to 28 October 2026, end exclusive. Files were actually retrieved from Earth Engine and processed by the installed MATLAB.

Selected observations:
- Sentinel-1: 7 October 2026 11:48:12 UTC and 19 October 2026 11:48:12 UTC; ascending, relative orbit 143, VV/VH.
- Sentinel-2: 14 October 2026 04:31:07.091 UTC and 19 October 2026 04:31:08.732 UTC; actual collection metadata retained.
- SRTM historical terrain, with slope and hillshade context.

Common export grid: EPSG:32646, 10 m. MATLAB output valid fraction: 0.8576687116564418. Candidate count: 0. Processing timestamp: 28 October 2026 18:39:59 UTC (29 October 2026 00:09:59 IST). This is an integration result for a test corridor, **not a road-safety conclusion**.

The live test exposed two software issues missed by initial unit checks: incompatible Earth Engine export parameters (region + transform + dimensions), and incorrect indexing of a single-band output array. Both were fixed. The valid-output regression test now covers the latter. Invalid raster previews and validity-mask inconsistencies are rejected.

## Unconfigured or not verified

- Google Maps JavaScript browser key and backend Routes API key are missing. Actual driving routes, alternatives, map rendering and Places suggestions therefore remain unverified. Suggestions additionally require Places API enablement and suitable browser-key restrictions.
- Full user route → queued worker → satellite → MATLAB → dashboard acceptance remains unverified because routing credentials are unavailable. The underlying satellite/MATLAB path was exercised separately.
- MATLAB Engine mode is implemented but not exercised; batch mode is verified.
- PostgreSQL/PostGIS migration and Docker Compose launch were not run; Docker was not available on PATH.
- Interactive wizard prompts, browser offline reconnection, uploaded-photo happy path and multi-worker concurrency were not exhaustively exercised.
- No calibrated model, labeled regional test dataset, detection accuracy or emergency operational validation exists.

## Environment notes

Windows sandbox networking prevented initial package retrieval, browser loopback access and in-process HTTP tests. Authorized network-capable execution resolved those checks. Initial MATLAB startup failed on a non-writable preferences directory and then MathWorks connectivity; workspace-local preferences and authorized network access resolved both. These were environment failures, not successful integration results at the time they occurred.

Tested dependency versions are recorded in `backend/requirements-tested-windows.txt` and `frontend/pnpm-lock.yaml`. General cross-platform dependency ranges remain in `backend/requirements.txt`.
