import asyncio
from contextlib import suppress
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_user_from_access_token
from app.core.exceptions import AppError
from app.db.session import get_db_session
from app.services.attendance_realtime_service import (
    OPERATIONS_ROLES,
    AttendanceRealtimeConnection,
    attendance_realtime_hub,
    heartbeat_payload,
)

router = APIRouter(prefix="/attendance", tags=["attendance realtime"])
ALLOWED_ROLES = {"member", *OPERATIONS_ROLES}
AUTHENTICATION_TIMEOUT_SECONDS = 5.0


@router.websocket("/realtime")
async def attendance_realtime(
    websocket: WebSocket,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await websocket.accept()
    connection: AttendanceRealtimeConnection | None = None
    tasks: list[asyncio.Task[None]] = []
    try:
        try:
            frame = await asyncio.wait_for(websocket.receive_json(), timeout=AUTHENTICATION_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await websocket.close(code=4408, reason="Authentication timed out")
            return
        except (ValueError, TypeError):
            await websocket.close(code=4400, reason="Malformed authentication frame")
            return

        if not isinstance(frame, dict) or frame.get("type") != "authenticate" or not isinstance(frame.get("access_token"), str):
            await websocket.close(code=4400, reason="Malformed authentication frame")
            return
        try:
            user = await get_user_from_access_token(frame["access_token"], session)
        except AppError:
            await websocket.close(code=4401, reason="Authentication failed")
            return
        if user.must_change_password or user.role not in ALLOWED_ROLES:
            await websocket.close(code=4403, reason="Attendance updates are not available for this account")
            return

        connection = await attendance_realtime_hub.register(role=user.role, user_id=user.id)
        connection.queue.put_nowait(
            {"type": "subscribed", "scope": "member" if user.role == "member" else "operations"},
        )
        connection.queue.put_nowait({"type": "resync_required"})
        tasks = [
            asyncio.create_task(_send_messages(websocket, connection)),
            asyncio.create_task(_receive_messages(websocket, connection)),
            asyncio.create_task(_heartbeat(websocket, connection)),
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if not task.cancelled():
                task.result()
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError, WebSocketDisconnect):
                await task
        if connection:
            await attendance_realtime_hub.unregister(connection.connection_id)


async def _send_messages(websocket: WebSocket, connection: AttendanceRealtimeConnection) -> None:
    while True:
        await websocket.send_json(await connection.queue.get())


async def _receive_messages(websocket: WebSocket, connection: AttendanceRealtimeConnection) -> None:
    while True:
        frame = await websocket.receive_json()
        if not isinstance(frame, dict) or frame.get("type") != "pong":
            await websocket.close(code=4400, reason="Unsupported realtime frame")
            return
        connection.last_pong_at = monotonic()


async def _heartbeat(websocket: WebSocket, connection: AttendanceRealtimeConnection) -> None:
    while True:
        await asyncio.sleep(20)
        if monotonic() - connection.last_pong_at > 50:
            await websocket.close(code=4408, reason="Heartbeat timed out")
            return
        try:
            connection.queue.put_nowait(heartbeat_payload())
        except asyncio.QueueFull:
            return
