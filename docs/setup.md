# Setup

Use Python 3.12, Node 22, pnpm, and a licensed MATLAB release with Image Processing Toolbox and Mapping Toolbox. Linux is supported with a valid Linux MATLAB installation. MATLAB Runtime cannot run the uncompiled scripts.

Run the README commands from the repository root. The wizard asks for all project IDs, both Maps keys, API/billing confirmation, allowed origins, restrictions, Earth Engine authentication and MATLAB configuration. Secrets use hidden terminal input. The `.env` file is ignored by Git; restrict its filesystem permissions. Do not supply private credentials through the web interface.

## Google Maps

1. Select your actual project in Google Cloud Console. Link a billing account.
2. Enable Maps JavaScript API and Routes API.
3. Create a browser key, restrict it to Maps JavaScript API (and Places API if using suggestions), and restrict HTTP referrers to your actual development/production origins.
4. Create a separate server key restricted to Routes API and appropriate server egress IPs.
5. Enter the keys through `python scripts/setup_wizard.py`. Do not use `VITE_MAPS_ROUTES_KEY` or any other frontend variable for the backend key.
6. Run `python scripts/check_integrations.py`. The Routes check makes one actual Itanagar–Naharlagun request, which may incur provider charges. Browser-key success must be checked by loading the real map on an allowed origin. The checker intentionally does not mark browser configuration PASS.

Maps Routes uses `DRIVE`, alternatives, high-quality GeoJSON polylines, and an explicit field mask. Place names and latitude,longitude are supported. No route is fabricated when routing fails. Maps is not an independent closure verification source.

Official references:
- https://developers.google.com/maps/documentation/routes/compute_route_directions
- https://developers.google.com/maps/documentation/routes/traffic_on_polylines
- https://developers.google.com/maps/api-security-best-practices

## SQLite

Default `DATABASE_URL=sqlite:///./data/app.sqlite`. Run migrations first. Use one API process and one worker. SQLite WAL and a busy timeout allow the development API and worker to share the database.

## PostgreSQL/PostGIS and Docker

Set a strong URL-safe `POSTGRES_PASSWORD` in `.env`, then:

```powershell
docker compose up --build db migrate api frontend
```

Open http://localhost:8080. The database binds only loopback. API and frontend also bind loopback. The host-native worker uses the same project/data folder and:

```powershell
# Set this privately; do not paste the real password in shared logs.
$env:DATABASE_URL = 'postgresql+psycopg://hillwatch:YOUR_PASSWORD@localhost:5432/hillwatch'
$env:PYTHONPATH = "$PWD/backend"
python -m app.jobs
```

The compose stack intentionally does not pretend to contain MATLAB. A Windows license/executable cannot run in the Linux API container. Run integration checks on the worker host; the API reads the shared status file. For a Linux MATLAB worker, mount your authorized installation/license and shared data explicitly.

For external deployment configure HTTPS, secure cookies, exact CORS origins, restricted keys, authentication provisioning, shared rate limiting and managed identity. Do not expose the development server publicly.
