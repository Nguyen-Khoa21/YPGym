import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from payos import WebhookError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.core.exceptions import AppError
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.class_schema import BookingRefundResolution
from app.schemas.payment_schema import PayOSCreateRequest, PayOSCreateResponse, PayOSWebhookResponse, PaymentStatusResponse
from app.services.payment_service import PayOSPaymentService
from app.utils.security import hash_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/payos/create", response_model=PayOSCreateResponse, status_code=201)
async def create_payos_payment(
    payload: PayOSCreateRequest,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> PayOSCreateResponse:
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:payos-create:{hash_token(str(current_user.id))}",
        limit=10,
        window_seconds=60,
    )
    return await PayOSPaymentService(session).create_payment(user=current_user, payload=payload)


@router.post("/payos/webhook", response_model=PayOSWebhookResponse)
async def payos_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    content_length = request.headers.get("content-length")
    try:
        declared_length = int(content_length) if content_length else None
    except ValueError:
        declared_length = None
    if declared_length is not None and declared_length > 65_536:
        raise AppError("PAYOS_WEBHOOK_TOO_LARGE", "Webhook payload is too large.", 413)
    payload = await request.body()
    if len(payload) > 65_536:
        raise AppError("PAYOS_WEBHOOK_TOO_LARGE", "Webhook payload is too large.", 413)
    try:
        return await PayOSPaymentService(session).process_webhook(payload)
    except WebhookError as exc:
        await session.rollback()
        logger.warning("payos_webhook_rejected exception_type=%s", type(exc).__name__)
        raise AppError("PAYOS_SIGNATURE_INVALID", "Webhook signature is invalid.", 400) from exc


@router.get("/payos/{order_code}", response_model=PaymentStatusResponse)
async def get_payos_payment_status(
    order_code: int,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentStatusResponse:
    return await PayOSPaymentService(session).get_status_by_order_code(user=current_user, order_code=order_code)


@router.get("/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentStatusResponse:
    return await PayOSPaymentService(session).get_status(user=current_user, payment_id=payment_id)


@router.post("/{payment_id}/resolve-class-refund", response_model=PaymentStatusResponse)
async def resolve_class_refund(
    payment_id: UUID,
    payload: BookingRefundResolution,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentStatusResponse:
    return await PayOSPaymentService(session).resolve_class_refund(
        payment_id=payment_id,
        actor=current_user,
        reason=payload.reason,
    )
