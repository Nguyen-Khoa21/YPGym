"""Bounded benchmark with real synthetic accounts, only on the standalone test stack.

Run from /app as python -m scripts.registered_load after Alembic migrations.
No storage is deleted. Refuses any non-test database and any non-empty user table.
"""
import argparse
import asyncio
import json
import os
import platform
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from sqlalchemy import event, func, select, text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, engine
from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.classes import ClassBooking, GymClass
from app.models.membership import MembershipPlan, UserMembership
from app.models.user import User
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.class_repository import ClassRepository
from app.repositories.operations_repository import AuditRepository, BillingAdminRepository, CrmRepository
from app.utils.security import hash_password
from scripts.load_smoke import run_probe


async def review_queries(users):
    """Measure existing repository queries; never print SQL parameters or filters."""
    report = {}
    async with AsyncSessionLocal() as session:
        await session.execute(text("ANALYZE"))
        billing = BillingAdminRepository(session)
        filters = dict(member=None, status=None, date_from=None, date_to=None, plan=None, tier=None)
        operations = {
            "crm": (CrmRepository(session).list_members, dict(search=None, role=None, tier=None, status=None, expiry_from=None, expiry_to=None, sort_by="created_at", sort_order="desc")),
            "payments": (billing.list_payments, filters),
            "invoices": (billing.list_invoices, filters),
            "audit": (AuditRepository(session).list_filtered, {}),
            "attendance": (AttendanceRepository(session).list_admin_sessions, dict(date_from=None, date_to=None, status=None, member=None)),
        }
        statements = []

        def capture(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append((statement, parameters))

        for name, (operation, options) in operations.items():
            query_counts = {}
            for size in (20, 100):
                statements.clear()
                event.listen(engine.sync_engine, "before_cursor_execute", capture)
                try:
                    first = await operation(page=1, page_size=size, **options)
                    query_counts[str(size)] = len(statements)
                finally:
                    event.remove(engine.sync_engine, "before_cursor_execute", capture)
                assert len(first[0]) <= size
                second = await operation(page=2, page_size=size, **options)
                assert first[1] == second[1]
                assert not ({row[0].id for row in first[0]} & {row[0].id for row in second[0]})
            report[name] = {"total_rows": first[1], "selects_per_page": query_counts, "plans": []}
            async with engine.connect() as connection:
                for statement, parameters in statements:
                    result = await connection.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters)
                    plan = result.scalar_one()[0]
                    nodes = [plan["Plan"]]
                    scans = []
                    while nodes:
                        node = nodes.pop()
                        if "Scan" in node["Node Type"]:
                            scans.append({key: node[key] for key in ("Node Type", "Relation Name", "Index Name", "Actual Rows", "Actual Loops") if key in node})
                        nodes.extend(node.get("Plans", []))
                    report[name]["plans"].append({"planning_ms": plan["Planning Time"], "execution_ms": plan["Execution Time"], "shared_hits": plan["Plan"].get("Shared Hit Blocks", 0), "shared_reads": plan["Plan"].get("Shared Read Blocks", 0), "scans": scans})
        # Member class cards use one joined statement with a correlated booking
        # aggregate, rather than a separate API/SQL query for each class.
        statements.clear()
        event.listen(engine.sync_engine, "before_cursor_execute", capture)
        try:
            classes = await ClassRepository(session).member_classes(user_id=users[0].id)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", capture)
        report["member_classes"] = {"rows": len(classes), "selects": len(statements)}
    return report


async def main(query_review_only=False):
    settings = get_settings()
    if (settings.ENVIRONMENT, urlsplit(settings.DATABASE_URL).hostname, urlsplit(settings.DATABASE_URL).path, urlsplit(settings.REDIS_URL).hostname) != ("test", "test-postgres", "/ypgym_test", "test-redis"):
        raise RuntimeError("This benchmark requires the standalone compose.test.yml storage")
    password = "Synthetic-benchmark-only-123!"
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        if (await session.execute(select(func.count(User.id)))).scalar_one() != 0:
            raise RuntimeError("Benchmark requires an empty user table; start fresh disposable test resources")
        password_hash = hash_password(password)
        users = [User(id=uuid4(), name=f"Synthetic member {i}", email=f"load-{i}@example.com", phone=f"090{i:07d}", password_hash=password_hash, is_email_verified=True) for i in range(1000)]
        plan = MembershipPlan(id=uuid4(), name="Synthetic monthly", duration_months=1, duration_days=30, base_price=Decimal("720000"))
        classes = [GymClass(id=uuid4(), title=f"Synthetic class {i}", class_type="Strength", capacity=25, start_at=now + timedelta(days=i // 10 + 1, hours=i % 10), end_at=now + timedelta(days=i // 10 + 1, hours=i % 10 + 1), location="Test studio") for i in range(100)]
        session.add_all([plan, *users, *classes])
        await session.flush()
        visits = [AttendanceSession(id=uuid4(), user_id=user.id, checked_in_at=now - timedelta(days=1, hours=1), closed_at=now - timedelta(days=1), status="checked_out") for user in users]
        session.add_all(visits)
        session.add_all([UserMembership(user_id=user.id, plan_id=plan.id, start_date=now.date(), expiry_date=now.date() + timedelta(days=30), status="active") for user in users])
        session.add_all([ClassBooking(class_id=item.id, user_id=users[(index * 20 + offset) % 1000].id, status="booked") for index, item in enumerate(classes) for offset in range(20)])
        await session.flush()
        session.add_all([AttendanceEvent(session_id=visit.id, user_id=visit.user_id, event_type="check_in", event_at=visit.checked_in_at, source="synthetic_benchmark") for visit in visits])
        await session.commit()
        counts = {model.__tablename__: (await session.execute(select(func.count()).select_from(model))).scalar_one() for model in (User, UserMembership, GymClass, ClassBooking, AttendanceSession)}

    query_review = await review_queries(users)
    if query_review_only:
        print(json.dumps({"measured_at": datetime.now(UTC).isoformat(), "dataset": counts, "query_review": query_review}, indent=2))
        await engine.dispose()
        return

    # The actual Uvicorn HTTP stack runs on container loopback; auth is unmodified.
    server = await asyncio.create_subprocess_exec(sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:
            for _ in range(100):
                try:
                    if (await client.get("/api/v1/health")).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise RuntimeError("Isolated API did not become healthy")
            token = None

            def remember_login(response):
                nonlocal token
                if response.status_code == 200 and token is None:
                    token = response.json()["access_token"]

            result = {
                "measured_at": datetime.now(UTC).isoformat(),
                "runtime": {"python": platform.python_version(), "platform": platform.platform(), "visible_cpu_count": os.cpu_count()},
                "dataset": counts,
                "query_review": query_review,
                "transport": "Uvicorn HTTP over isolated container loopback, one worker",
                "login": await run_probe(client, method="POST", path="/api/v1/auth/login", concurrency=10, total=1000, json_body=lambda i: {"email": f"load-{i}@example.com", "password": password}, on_response=remember_login),
            }
            if token is None:
                raise RuntimeError("No benchmark login succeeded; protected probes cannot run")
            for path in ("/api/v1/attendance/crowdedness", "/api/v1/classes/upcoming"):
                result[path] = await run_probe(client, method="GET", path=path, concurrency=10, total=1000, headers={"Authorization": f"Bearer {token}"})
            print(json.dumps(result, indent=2))
            if any(probe["errors"] or any(int(status) >= 500 for status in probe["statuses"]) for probe in (result["login"], result["/api/v1/attendance/crowdedness"], result["/api/v1/classes/upcoming"])):
                raise RuntimeError("Benchmark recorded transport or server failures; inspect aggregate output")
    finally:
        server.terminate()
        await server.wait()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query-review-only", action="store_true", help="Create the same isolated dataset and inspect query plans/pages without HTTP load waves")
    asyncio.run(main(parser.parse_args().query_review_only))
