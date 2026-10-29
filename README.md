# Hillwatch Northeast

An experimental hill-road terrain-change and incident-review application for NORTHEAST Coding Pundit PS-03. React/TypeScript/Vite frontend, FastAPI backend, durable database jobs, Google Routes, Earth Engine, and real MATLAB `.m` processing. There is no synthetic fallback in real mode.

**A landslide candidate is not a confirmed landslide. Corridor overlap is not proof of blockage. No detected change does not establish a clear road.** No government affiliation or scientific accuracy is claimed.

## Start locally (Windows PowerShell, Python 3.12 and Node 22)

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python scripts/setup_wizard.py
python scripts/migrate.py
python scripts/create_user.py reviewer --role Reviewer
python scripts/create_user.py roadteam --role "Road Authority"
python scripts/check_integrations.py
$env:PYTHONPATH = "$PWD/backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, activate the environment, set `PYTHONPATH`, and run the durable worker:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD/backend"
python -m app.jobs
```

In a third terminal:

```powershell
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

Open **http://localhost:5173**. API documentation: **http://localhost:8000/docs**. `localhost` and `127.0.0.1` are different origins: use the same hostname consistently, or add both to `ALLOWED_ORIGINS` and the browser-key restrictions. Vite proxies `/api`, so no server API key is bundled.

The supplied local `.env` records only the user-provided Earth Engine project ID and detected MATLAB path. The ZIP omits `.env`, credentials, local data and dependencies. Copy `.env.example` or run the wizard after extraction.

## Verify

```powershell
python -m pytest backend/tests -q
cd frontend
pnpm build
```

For licensed MATLAB with both toolboxes:

```powershell
& 'E:\mat\bin\matlab.exe' -batch "addpath('matlab'); results=runtests('matlab/test_pipeline.m'); assertSuccess(results);"
```

See `docs/verification.md` for what was actually executed in the build environment. Unit tests use explicitly simulated fixtures and do not verify live Google services or scientific accuracy.

## Included

- Origin/destination routing, alternatives, map selection, bounded metric corridors and ordered 2 km sections.
- Recent-image search with configurable historical fallback, matching SAR orbits, valid-coverage selection, SCL-masked optical exports, SRTM terrain, actual scene provenance and PNG previews.
- MATLAB batch/Engine adapters, input validation, speckle filtering, dB differencing, local statistics, NDVI loss support, slope gating, component filtering, change masks and vector candidates.
- Database jobs with progress, cancellation, timeout, bounded downloads, retry and worker-interruption detection.
- Public incident reports, duplicates, stale flags, offline text queue, optional authenticated photos, reviewer queue, role-restricted verification/closure, audit history and JSON export.
- Separate landslide, road-impact, unverified-report, official-closure and freshness fields.
- Private configuration wizard, integration checks, migrations, Docker assets, tests and API schemas.

## Read next

- [Setup and Google Maps](docs/setup.md)
- [Earth Engine](docs/gee_setup.md)
- [MATLAB](docs/matlab_setup.md)
- [Architecture and data flow](docs/architecture.md)
- [API reference](docs/api.md)
- [Scientific and operational limits](docs/limitations.md)
- [Troubleshooting and demonstration](docs/troubleshooting.md)
- [Source inspection](docs/source_inspection.md)

This is an engineering implementation requiring live acceptance testing and scientific validation before operational use. Do not deploy it as an emergency navigation authority.
