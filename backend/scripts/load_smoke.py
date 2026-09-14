"""Small repeatable load probe for the Day54 release gate.

It creates no database rows. Login probes use unique synthetic email addresses;
authenticated endpoint probes require YPGYM_LOAD_TOKEN and reuse that token only
for read-only requests.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
from collections import Counter
from collections.abc import Callable

import httpx


async def run_probe(
    client: httpx.AsyncClient,
    *,
    method: str,
    path: str,
    concurrency: int,
    total: int,
    json_body: dict | Callable[[int], dict] | None = None,
    headers: dict[str, str] | None = None,
    on_response: Callable[[httpx.Response], None] | None = None,
) -> dict[str, object]:
    semaphore = asyncio.Semaphore(concurrency)
    durations: list[float] = []
    statuses: Counter[int] = Counter()
    errors: Counter[str] = Counter()

    async def one(index: int) -> None:
        async with semaphore:
            started = time.perf_counter()
            body = json_body(index) if callable(json_body) else json_body
            try:
                response = await client.request(method, path, json=body, headers=headers)
            except httpx.HTTPError as exc:
                errors[type(exc).__name__] += 1
                durations.append((time.perf_counter() - started) * 1000)
                return
            durations.append((time.perf_counter() - started) * 1000)
            statuses[response.status_code] += 1
            if on_response is not None:
                on_response(response)

    started = time.perf_counter()
    await asyncio.gather(*(one(index) for index in range(total)))
    elapsed = time.perf_counter() - started
    ordered = sorted(durations)
    percentile = lambda value: ordered[min(len(ordered) - 1, int(len(ordered) * value))]
    return {
        "requests": total,
        "concurrency": concurrency,
        "duration_seconds": round(elapsed, 3),
        "requests_per_second": round(total / elapsed, 2),
        "statuses": dict(sorted(statuses.items())),
        "errors": dict(sorted(errors.items())),
        "min_ms": round(ordered[0], 2),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(percentile(0.95), 2),
        "max_ms": round(ordered[-1], 2),
    }


async def main(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout) as client:
        login = await run_probe(
            client,
            method="POST",
            path="/api/v1/auth/login",
            concurrency=args.concurrency,
            total=args.users,
            json_body=lambda index: {
                "email": f"load-{args.run_id}-{index}@example.com",
                "password": "synthetic-load-password",
            },
        )
        print({"login": login})

        token = os.environ.get("YPGYM_LOAD_TOKEN")
        if not token:
            print({"authenticated": "skipped; set YPGYM_LOAD_TOKEN for read-only endpoint probes"})
            return
        headers = {"Authorization": f"Bearer {token}"}
        for path in ("/api/v1/attendance/crowdedness", "/api/v1/classes/upcoming"):
            result = await run_probe(
                client,
                method="GET",
                path=path,
                concurrency=args.concurrency,
                total=args.auth_requests,
                headers=headers,
            )
            print({path: result})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--auth-requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--run-id", default=str(int(time.time())))
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
