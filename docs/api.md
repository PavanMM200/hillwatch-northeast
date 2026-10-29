# API

The executable schema is exposed at `/openapi.json` and interactive documentation at `/docs`. `docs/openapi.json` is generated from the application during validation when dependencies are available.

All mutation requests need `X-Requested-With: Hillwatch`. Browser requests must originate from a configured origin. Official operations additionally require an HTTP-only session cookie obtained from login. JSON errors are `{code,message}`; validation errors use FastAPI's structured `detail` array. No raw upstream response bodies, tokens or credentials are returned.

| Method / path | Input and result |
|---|---|
| GET `/api/health` | Service timestamp, real mode, experimental method |
| GET `/api/public-config` | Restricted browser key only; no server credentials |
| GET `/api/integrations/status` | Configured flag, actual check state/date and actionable message |
| POST `/api/auth/login` | `{username,password}` → session cookie and role |
| POST `/api/auth/logout` | Revoke current session |
| GET `/api/auth/me` | Current username/role |
| POST `/api/routes/compute` | `{origin,destination,corridor_m:300}` → actual alternatives, IDs, geometry, segments, distance, duration |
| POST `/api/analyses` | `{route_id,start_date,end_date,fallback_days:90}` → 202 durable job |
| GET `/api/analyses/{id}` | State, progress, safe error, request and partial progress payload |
| POST `/api/analyses/{id}/cancel` | Queued → cancelled; running → cancel_requested |
| GET `/api/analyses/{id}/results` | Validated section results with current evidence status; 409 before ready |
| GET `/api/analyses/{id}/artifacts` | Download IDs/names/sizes/URLs; no arbitrary paths |
| GET `/api/analyses/{id}/artifacts/{artifact_id}` | Allowlisted validated generated file |
| POST `/api/incidents` | See below; always UNVERIFIED initially |
| GET `/api/incidents?offset=0&limit=30` | Paginated public non-rejected incidents, max 100 |
| GET `/api/incidents/{id}` | Public incident details, both timestamps, stale/duplicate flags |
| POST `/api/incidents/{id}/flag` | Flag for review; does not auto-change verification |
| POST `/api/incidents/{id}/photo` | Authenticated multipart JPEG/PNG, max 5 MiB, EXIF stripped |
| POST `/api/incidents/{id}/verify` | Reviewer/Authority/Admin; closure restricted to Authority/Admin |
| PATCH `/api/incidents/{id}/status` | Authority/Admin `{status:ACTIVE or RESOLVED,notes}` |
| GET `/api/official/queue` | Reviewer/Authority/Admin paginated queue, includes rejected entries |
| GET `/api/official/audit` | Reviewer/Authority/Admin paginated audit |
| GET `/api/official/export` | Reviewer/Authority/Admin JSON export, max 10,000 records |
| GET `/api/official/incidents/{id}/photo` | Reviewer/Authority/Admin photograph |

Incident request:
```json
{
  "client_id": "a client-generated UUID for idempotency",
  "kind": "BLOCKAGE",
  "latitude": 27.09,
  "longitude": 93.62,
  "observed_at": "ISO-8601 timestamp with timezone",
  "description": "An actual observation of 10 to 3000 characters",
  "direction": null,
  "route_id": null,
  "segment_id": null
}
```
Coordinates above illustrate the schema only; they are not a real incident. Supported types: LANDSLIDE, BLOCKAGE, DEBRIS, OTHER. Observation time cannot be in the future. Server submission time is generated independently.

Verification: `decision` VERIFIED/REJECTED, `notes`, `source`, `observed_at`, `expires_at`, `closure` boolean. Timezone required; validity at most seven days. Latest decision supersedes older assertions. Application permissions alone do not validate real-world source credibility.

Job states: queued, running, cancel_requested, cancelled, completed, partial, failed. `partial` means some sections lack valid results; inspect every section. Results never condense uncertainty into an unexplained score.
