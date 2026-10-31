import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID, uuid4

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.schemas.attendance_schema import AttendanceRealtimeEvent, CrowdednessResponse

logger = logging.getLogger(__name__)

ATTENDANCE_REALTIME_CHANNEL = "ypgym:attendance:events:v1"
OPERATIONS_ROLES = {"staff", "manager", "admin"}


class AttendanceRealtimePublisher:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish_transition(
        self,
        *,
        action: str,
        user_id: UUID,
        session_id: UUID,
        occurred_at: datetime,
        occupancy: CrowdednessResponse,
        request_id: str,
        include_occupancy: bool = True,
    ) -> None:
        events = [
            AttendanceRealtimeEvent(
                event_id=uuid4(),
                kind="attendance_changed",
                action=action,
                user_id=user_id,
                session_id=session_id,
                occurred_at=occurred_at,
                occupancy_calculated_at=occupancy.calculated_at,
                request_id=request_id,
            ),
        ]
        if include_occupancy:
            events.append(
                AttendanceRealtimeEvent(
                    event_id=uuid4(),
                    kind="occupancy_changed",
                    action=action,
                    occurred_at=occurred_at,
                    occupancy_calculated_at=occupancy.calculated_at,
                    request_id=request_id,
                ),
            )
        await self.publish(events)

    async def publish(self, events: list[AttendanceRealtimeEvent]) -> None:
        for event in events:
            try:
                await asyncio.wait_for(
                    self.redis.publish(ATTENDANCE_REALTIME_CHANNEL, event.model_dump_json()),
                    timeout=1.0,
                )
            except (RedisError, OSError, asyncio.TimeoutError):
                # Attendance is already committed. Realtime delivery is best-effort
                # invalidation and must never make the durable transition fail.
                logger.warning(
                    "attendance_realtime_publish_failed event_id=%s kind=%s request_id=%s",
                    event.event_id,
                    event.kind,
                    event.request_id,
                )


@dataclass(slots=True)
class AttendanceRealtimeConnection:
    connection_id: UUID
    role: str
    user_id: UUID
    queue: asyncio.Queue[dict[str, object]] = field(default_factory=lambda: asyncio.Queue(maxsize=20))
    last_pong_at: float = field(default_factory=monotonic)


class AttendanceRealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[UUID, AttendanceRealtimeConnection] = {}
        self._lock = asyncio.Lock()
        self._listener_task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        self._stopping.clear()
        self._listener_task = asyncio.create_task(self._listen_forever(), name="attendance-realtime-listener")

    async def stop(self) -> None:
        self._stopping.set()
        task = self._listener_task
        self._listener_task = None
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        async with self._lock:
            self._connections.clear()

    async def register(self, *, role: str, user_id: UUID) -> AttendanceRealtimeConnection:
        connection = AttendanceRealtimeConnection(connection_id=uuid4(), role=role, user_id=user_id)
        async with self._lock:
            self._connections[connection.connection_id] = connection
        return connection

    async def unregister(self, connection_id: UUID) -> None:
        async with self._lock:
            self._connections.pop(connection_id, None)

    async def dispatch(self, event: AttendanceRealtimeEvent) -> None:
        async with self._lock:
            connections = list(self._connections.values())
        for connection in connections:
            payload = self._payload_for(connection, event)
            if payload is not None:
                self._enqueue(connection, payload)

    async def request_resync(self) -> None:
        async with self._lock:
            connections = list(self._connections.values())
        for connection in connections:
            self._enqueue(connection, {"type": "resync_required"})

    @staticmethod
    def _payload_for(
        connection: AttendanceRealtimeConnection,
        event: AttendanceRealtimeEvent,
    ) -> dict[str, object] | None:
        if connection.role == "member":
            if event.kind == "attendance_changed" and event.user_id != connection.user_id:
                return None
            return {
                "type": event.kind,
                "event_id": str(event.event_id),
                "action": event.action,
                "session_id": str(event.session_id) if event.session_id and event.user_id == connection.user_id else None,
                "occurred_at": event.occurred_at.isoformat(),
                "occupancy_calculated_at": event.occupancy_calculated_at.isoformat(),
            }
        if connection.role in OPERATIONS_ROLES:
            return {
                "type": event.kind,
                "event_id": str(event.event_id),
                "action": event.action,
                "session_id": str(event.session_id) if event.session_id else None,
                "occurred_at": event.occurred_at.isoformat(),
                "occupancy_calculated_at": event.occupancy_calculated_at.isoformat(),
            }
        return None

    @staticmethod
    def _enqueue(connection: AttendanceRealtimeConnection, payload: dict[str, object]) -> None:
        if connection.queue.full():
            while not connection.queue.empty():
                with suppress(asyncio.QueueEmpty):
                    connection.queue.get_nowait()
            payload = {"type": "resync_required"}
        with suppress(asyncio.QueueFull):
            connection.queue.put_nowait(payload)

    async def _listen_forever(self) -> None:
        delay = 0.5
        reconnecting = False
        while not self._stopping.is_set():
            client = Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
            pubsub = client.pubsub()
            try:
                await pubsub.subscribe(ATTENDANCE_REALTIME_CHANNEL)
                if reconnecting:
                    await self.request_resync()
                reconnecting = False
                delay = 0.5
                while not self._stopping.is_set():
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if not message:
                        continue
                    try:
                        event = AttendanceRealtimeEvent.model_validate_json(message["data"])
                    except (ValidationError, TypeError, ValueError):
                        logger.warning("attendance_realtime_invalid_event")
                        continue
                    await self.dispatch(event)
            except asyncio.CancelledError:
                raise
            except (RedisError, OSError):
                reconnecting = True
                logger.warning("attendance_realtime_listener_unavailable")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10.0)
            finally:
                with suppress(Exception):
                    await pubsub.aclose()
                with suppress(Exception):
                    await client.aclose()


attendance_realtime_hub = AttendanceRealtimeHub()


def realtime_request_id(value: str | None = None) -> str:
    if value:
        return value[:128]
    return str(uuid4())


def heartbeat_payload() -> dict[str, str]:
    return {"type": "ping", "sent_at": datetime.now(UTC).isoformat()}
