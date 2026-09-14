"""Real storage tests, gated to the standalone compose.test.yml resources."""
import os
from urllib.parse import urlsplit

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest_asyncio.fixture
async def storage():
    if os.environ.get("ENVIRONMENT") != "test":
        pytest.skip("Run with compose.test.yml for isolated PostgreSQL/Redis integration tests")
    database_url = os.environ["DATABASE_URL"]
    redis_url = os.environ["REDIS_URL"]
    if (urlsplit(database_url).hostname, urlsplit(database_url).path, urlsplit(redis_url).hostname) != (
        "test-postgres", "/ypgym_test", "test-redis",
    ):
        pytest.fail("Refusing to reset storage outside the standalone test stack")

    from app.db.base import Base
    import app.models  # noqa: F401 — register the existing models

    engine = create_async_engine(database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        async with engine.begin() as connection:
            tables = ", ".join(f'"{name}"' for name in Base.metadata.tables)
            await connection.execute(text(f"TRUNCATE {tables} CASCADE"))
        await redis.flushdb()
        yield sessions, redis
    finally:
        await redis.aclose()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(storage):
    from app.main import app
    from app.db.session import get_db_session
    from app.db.redis import get_redis_client

    sessions, redis = storage

    async def session_dependency():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db_session] = session_dependency
    app.dependency_overrides[get_redis_client] = lambda: redis
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def eligible_members(storage):
    from datetime import date, timedelta
    from decimal import Decimal
    from uuid import uuid4
    from app.models.membership import MembershipPlan, UserMembership
    from app.models.user import User
    from app.utils.security import create_access_token

    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        plan = MembershipPlan(id=uuid4(), name="Integration monthly", duration_months=1, duration_days=30, base_price=Decimal("720000"))
        users = [User(id=uuid4(), name=f"Member {i}", email=f"eligible{i}@example.com", phone=f"12345678{i}", password_hash="unused", is_email_verified=True) for i in range(3)]
        session.add_all([plan, *users])
        await session.flush()
        session.add_all([UserMembership(user_id=user.id, plan_id=plan.id, status="active", start_date=today, expiry_date=today + timedelta(days=30)) for user in users])
        await session.commit()
    headers = [{"Authorization": f"Bearer {create_access_token(user_id=user.id, role='member', tier='normal')[0]}"} for user in users]
    return users, headers
