# Day54 performance evidence

Measured September 14, 2026 at 11:54 UTC on disposable PostgreSQL/Redis. The new backend/scripts/registered_load.py creates actual synthetic accounts and runs a single Uvicorn process over HTTP on container loopback. It refuses non-test storage and a non-empty user table, and never deletes data. load_smoke.py provides the bounded HTTP probe.

## Reproduce

From C:\Users\Admin\ypgym, with the standalone test stack stopped and no benchmark/tests running:

```powershell
docker compose -p ypgym-tests -f compose.test.yml run --rm test-runner sh -c 'alembic upgrade head && python -m scripts.registered_load'
docker compose -p ypgym-tests -f compose.test.yml stop
```

Build the runner first if absent: `docker compose -p ypgym-tests -f compose.test.yml build test-runner`. Stopping releases only these services' temporary PostgreSQL data. Before repeating a benchmark, ensure the test stack was stopped after the previous run. The script refuses populated storage. Never combine compose.test.yml with the normal application Compose file.

## Dataset and environment

- Verified row counts: 1,000 email-verified member accounts, 1,000 active memberships, 100 upcoming classes, 2,000 confirmed bookings, 1,000 closed attendance sessions. Setup also creates 1,000 check-in events.
- Accounts are inserted through existing SQLAlchemy models for setup, sharing a synthetic password/hash. Accepted logins perform real bcrypt verification. API registration/verification is tested separately by the integration suite.
- Host: AMD Ryzen 5 7535HS, 6 cores / 12 logical processors; 16,328,122,368 bytes physical memory.
- Docker engine 29.4.3: 12 visible CPUs, 7,905,304,576 bytes VM memory. Python 3.13.15, WSL2 Linux 6.6.114.1, PostgreSQL 16.14, Redis 7.4.9.
- One API worker; three sequential waves of 1,000 requests each, concurrency 10, 30-second request timeout. The normal development stack remained running alongside the isolated services. No dedicated CPU allocation or production network.
- Protected reads reuse one successful login's token. Occupancy includes ordinary cache misses/hits; classes returns the seeded upcoming classes. This does not simulate 1,000 concurrent sessions.

## Measured results

| Endpoint | HTTP outcomes | Duration | Requests/s | Median | p95 | Maximum |
|---|---|---:|---:|---:|---:|---:|
| Login | 60 × 200, 940 × 429 | 22.256 s | 44.93 | 49.07 ms | 2,085.44 ms | 3,372.68 ms |
| Crowdedness | 1,000 × 200 | 6.553 s | 152.59 | 50.76 ms | 148.25 ms | 388.95 ms |
| Upcoming classes | 1,000 × 200 | 13.121 s | 76.21 | 118.91 ms | 232.95 ms | 410.55 ms |

No transport exceptions or server errors. Login limits remained enabled: one source IP allowed 60 requests during its window. Login latency/throughput mixes successful authentication with inexpensive denials; it must not be presented as successful-login capacity. Per-request timings start after acquiring a concurrency slot. Wave duration includes the entire wave; percentiles use sorted observed samples.

This is a bounded local result with 1,000 stored accounts, not production capacity, 1,000 concurrent users or a multi-user session workload. Day54 remains in progress pending pagination/query-plan/index review. Final evidence must identify the eventual verified commit.

## Historical observation

The earlier development-stack load_smoke.py run created **no users**. Its 1,000 nonexistent-email requests yielded 999 × 401 and one ReadError (median 138.69 ms, p95 433.98 ms, maximum 5,518.58 ms). Earlier 100-request authenticated probes all returned 200: manager crowdedness p95 562.56 ms, member crowdedness p95 394.43 ms, classes p95 470.72 ms. That did not satisfy the stored-user requirement or measure bcrypt success. Changing run IDs cannot bypass the current IP limiter; 429 is intentional protection.
