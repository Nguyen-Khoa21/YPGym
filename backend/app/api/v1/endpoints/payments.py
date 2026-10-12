import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.payment_schema import (
    PaymentStatusResponse,
    VNPayCreateRequest,
    VNPayCreateResponse,
    VNPayIpnResponse,
)
from app.schemas.class_schema import BookingRefundResolution
from app.services.payment_service import VNPayPaymentService
from app.utils.security import hash_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


def _query_parameters(request: Request) -> dict[str, str] | None:
    items = list(request.query_params.multi_items())
    values = dict(items)
    return values if len(values) == len(items) else None


@router.post("/vnpay/create", response_model=VNPayCreateResponse, status_code=201)
async def create_vnpay_payment(
    payload: VNPayCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> VNPayCreateResponse:
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:vnpay-create:{hash_token(str(current_user.id))}",
        limit=10,
        window_seconds=60,
    )
    return await VNPayPaymentService(session).create_payment(
        user=current_user,
        payload=payload,
        client_ip=request.client.host if request.client else "127.0.0.1",
    )


@router.get("/vnpay/ipn", response_model=VNPayIpnResponse)
async def vnpay_ipn(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    parameters = _query_parameters(request)
    if parameters is None:
        return {"RspCode": "97", "Message": "Invalid signature"}
    try:
        return await VNPayPaymentService(session).process_ipn(parameters)
    except Exception as exc:
        await session.rollback()
        logger.error("vnpay_ipn_failed exception_type=%s", type(exc).__name__)
        return {"RspCode": "99", "Message": "Unknown error"}


@router.get("/vnpay/return", include_in_schema=False)
async def vnpay_return(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RedirectResponse:
    parameters = _query_parameters(request)
    target = await VNPayPaymentService(session).return_redirect(parameters or {})
    return RedirectResponse(target, status_code=302)


@router.get("/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentStatusResponse:
    return await VNPayPaymentService(session).get_status(user=current_user, payment_id=payment_id)


@router.post("/{payment_id}/resolve-class-refund", response_model=PaymentStatusResponse)
async def resolve_class_refund(
    payment_id: UUID,
    payload: BookingRefundResolution,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentStatusResponse:
    return await VNPayPaymentService(session).resolve_class_refund(
        payment_id=payment_id,
        actor=current_user,
        reason=payload.reason,
    )
