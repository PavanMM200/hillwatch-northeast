# Troubleshooting and demonstration

## Blockers

| Symptom | Action |
|---|---|
| Maps not configured | Run wizard; enter separate restricted browser/backend keys |
| Google HTTP 403 | Check API enablement, billing, key restrictions and project |
| Browser map blank | Check allowed referrer, Maps JavaScript API, browser network console and billing |
| EE_AUTH | Authenticate the selected method; check actual project registration and IAM |
| No SAR pair | Extend dates/fallback; inspect compatible orbit, VV/VH and coverage limitations |
| Optical absent | Cloud/shadow/coverage may be insufficient; no optical change is inferred |
| EE_EXPORT | Check quota/permissions/network; segments retry up to 3 times; no fake output |
| MATLAB preference folder error | Configure a writable MATLAB_WORK_DIR; adapter sets MATLAB_PREFDIR |
| MATLAB error 5201 | MATLAB could not communicate with required MathWorks services; resolve official licensing/network access with MathWorks or your administrator |
| Missing toolbox | Install/license Mapping Toolbox and Image Processing Toolbox |
| Grid mismatch | Check common UTM grid exports; never bypass validation or force mismatched images through |
| Job stays queued | Start `python -m app.jobs` with the same DB, config and shared data directory |
| Interrupted worker | Job becomes failed after heartbeat expiry; restart worker and submit a new job |
| Forbidden request | Match ALLOWED_ORIGINS and X-Requested-With header; sign in with correct role |
| Cookie unavailable | Use consistent hostnames and HTTPS when COOKIE_SECURE=true |
| pnpm esbuild script blocked | The project allowlists only esbuild in pnpm-workspace.yaml; reinstall with a supported pnpm version |

## Honest demonstration sequence

1. Show integration status and actual verification timestamps. If a service is unavailable, show the blocker rather than a fabricated result.
2. With keys configured, enter real locations, fetch alternatives and review actual provider distance/time. Select a corridor radius and dates.
3. Start the worker and analysis. Inspect section-level acquisition records, exported input comparisons, candidate polygons and quality limitations. Explain that the algorithm is experimental.
4. Submit a clearly labeled test report only to a separate test database. Verify it with a test reviewer account; demonstrate role restrictions on closure, source/expiry requirements and audit records.
5. Disconnect networking to demonstrate a queued text report. Reconnect and retry. Use a test database so demonstration reports cannot become real public incidents.
6. Run `pytest` and explain that simulated fixtures test software behavior, not real-world detection accuracy.

There is no seeded demonstration route, incident or satellite result. The test suite creates simulated data only in a temporary database. Never copy test results into the live database.

## Retention

Failed job imagery is removed; local diagnostic logs are retained. Completed job artifacts persist until an administrator applies a documented retention policy. Back up database and data together. Do not delete a job directory while it is running. Retain source/algorithm provenance for any published result.
