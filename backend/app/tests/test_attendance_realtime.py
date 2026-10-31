from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from starlette.websockets import WebSocketDisconnect

from app.api.v1.endpoints import attendance_realtime
from app.core.exceptions import AuthenticationError
from app.db.session import get_db_session
from app.schemas.attendance_schema import AttendanceRealtimeEvent, CrowdednessResponse
from app.services import attendance_realtime_service
from app.services.attendance_realtime_service import AttendanceRealtimeHub, AttendanceRealtimePublisher

def event(*, user_id=None, kind="attendance_changed") -> AttendanceRealtimeEvent:
    now = datetime.now(UTC)
    return AttendanceRealtimeEvent(
        event_id=uuid4(),
        kind=kind,
        action="check_in",
        user_id=user_id,
        session_id=uuid4() if user_id else None,
        occurred_at=now,
        occupancy_calculated_at=now,
        request_id=str(uuid4()),
    )


@pytest.mark.asyncio
async def test_member_stream_is_isolated_and_operations_receive_all_events():
    hub = AttendanceRealtimeHub()
    member_id = uuid4()
    other_member_id = uuid4()
    member = await hub.register(role="member", user_id=member_id)
    operations = await hub.register(role="staff", user_id=uuid4())

    await hub.dispatch(event(user_id=other_member_id))

    assert member.queue.empty()
    operations_payload = operations.queue.get_nowait()
    assert operations_payload["type"] == "attendance_changed"
    assert "user_id" not in operations_payload

    await hub.dispatch(event(user_id=member_id))
    member_payload = member.queue.get_nowait()
    assert member_payload["type"] == "attendance_changed"
    assert member_payload["session_id"]
    assert "user_id" not in member_payload


@pytest.mark.asyncio
async def test_occupancy_event_reaches_member_without_identity_and_overflow_requests_resync():
    hub = AttendanceRealtimeHub()
    member = await hub.register(role="member", user_id=uuid4())

    await hub.dispatch(event(kind="occupancy_changed"))
    payload = member.queue.get_nowait()
    assert payload["type"] == "occupancy_changed"
    assert "user_id" not in payload

    for index in range(21):
        hub._enqueue(member, {"type": "event", "index": index})
    assert member.queue.qsize() == 1
    assert member.queue.get_nowait() == {"type": "resync_required"}


@pytest.mark.asyncio
async def test_publish_failure_is_best_effort_and_logs_no_sensitive_material(caplog):
    secret = "raw-device-key-and-qr-material"

    class BrokenRedis:
        async def publish(self, *_args):
            raise RedisError(secret)

    now = datetime.now(UTC)
    publisher = AttendanceRealtimePublisher(BrokenRedis())
    await publisher.publish_transition(
        action="check_in",
        user_id=uuid4(),
        session_id=uuid4(),
        occurred_at=now,
        occupancy=CrowdednessResponse(active_count=1, capacity=10, percentage=10, status="Low", calculated_at=now),
        request_id="request-safe",
    )

    assert "attendance_realtime_publish_failed" in caplog.text
    assert secret not in caplog.text


@pytest.mark.asyncio
async def test_redis_listener_reconnect_requests_authoritative_resync(monkeypatch):
    hub = AttendanceRealtimeHub()
    connection = await hub.register(role="member", user_id=uuid4())

    class FailingPubSub:
        async def subscribe(self, *_args):
            raise RedisError("temporarily unavailable")

        async def aclose(self):
            return None

    class HealthyPubSub:
        async def subscribe(self, *_args):
            return None

        async def get_message(self, **_kwargs):
            hub._stopping.set()
            return None

        async def aclose(self):
            return None

    class FakeClient:
        def __init__(self, pubsub):
            self._pubsub = pubsub

        def pubsub(self):
            return self._pubsub

        async def aclose(self):
            return None

    clients = [FakeClient(FailingPubSub()), FakeClient(HealthyPubSub())]
    monkeypatch.setattr(attendance_realtime_service.Redis, "from_url", lambda *_args, **_kwargs: clients.pop(0))

    await hub._listen_forever()

    assert connection.queue.get_nowait() == {"type": "resync_required"}


def test_heartbeat_payload_contains_no_identity_or_credentials():
    payload = attendance_realtime_service.heartbeat_payload()
    assert payload["type"] == "ping"
    datetime.fromisoformat(payload["sent_at"])
    assert set(payload) == {"type", "sent_at"}


@pytest.mark.parametrize("role", ["member", "staff", "manager", "admin"])
def test_realtime_authenticates_allowed_roles_and_reconnects_with_resync(monkeypatch, role):
    user = SimpleNamespace(id=uuid4(), role=role, must_change_password=False)

    async def authenticated(_token, _session):
        return user

    monkeypatch.setattr(attendance_realtime, "get_user_from_access_token", authenticated)
    client = TestClient(realtime_test_app())
    for _ in range(2):
        with client.websocket_connect("/attendance/realtime") as websocket:
            websocket.send_json({"type": "authenticate", "access_token": "not-logged"})
            assert websocket.receive_json()["type"] == "subscribed"
            assert websocket.receive_json() == {"type": "resync_required"}


def test_realtime_rejects_malformed_expired_and_forbidden_auth(monkeypatch, caplog):
    client = TestClient(realtime_test_app())
    with pytest.raises(WebSocketDisconnect) as malformed:
        with client.websocket_connect("/attendance/realtime") as websocket:
            websocket.send_json({"type": "wrong"})
            websocket.receive_json()
    assert malformed.value.code == 4400

    async def expired(_token, _session):
        raise AuthenticationError("The access token is invalid.")

    monkeypatch.setattr(attendance_realtime, "get_user_from_access_token", expired)
    with pytest.raises(WebSocketDisconnect) as unauthorized:
        with client.websocket_connect("/attendance/realtime") as websocket:
            websocket.send_json({"type": "authenticate", "access_token": "sensitive-expired-token"})
            websocket.receive_json()
    assert unauthorized.value.code == 4401
    assert "sensitive-expired-token" not in caplog.text

    async def personal_trainer(_token, _session):
        return SimpleNamespace(id=uuid4(), role="personal_trainer", must_change_password=False)

    monkeypatch.setattr(attendance_realtime, "get_user_from_access_token", personal_trainer)
    with pytest.raises(WebSocketDisconnect) as forbidden:
        with client.websocket_connect("/attendance/realtime") as websocket:
            websocket.send_json({"type": "authenticate", "access_token": "not-logged"})
            websocket.receive_json()
    assert forbidden.value.code == 4403


def test_realtime_closes_when_authentication_frame_times_out(monkeypatch):
    monkeypatch.setattr(attendance_realtime, "AUTHENTICATION_TIMEOUT_SECONDS", 0.01)
    client = TestClient(realtime_test_app())
    with pytest.raises(WebSocketDisconnect) as timed_out:
        with client.websocket_connect("/attendance/realtime") as websocket:
            websocket.receive_json()
    assert timed_out.value.code == 4408


def realtime_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(attendance_realtime.router)

    async def session_override():
        yield None

    app.dependency_overrides[get_db_session] = session_override
    return app
