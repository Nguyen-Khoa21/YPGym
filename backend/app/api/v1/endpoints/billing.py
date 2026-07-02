from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.billing_schema import (
    AdminBillingItem,
    InvoiceHistoryItem,
    PaymentHistoryItem,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/me/payments", response_model=list[PaymentHistoryItem])
async def list_my_payments(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PaymentHistoryItem]:
    return await BillingService(session).list_my_payments(current_user)


@router.get("/me/invoices", response_model=list[InvoiceHistoryItem])
async def list_my_invoices(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[InvoiceHistoryItem]:
    return await BillingService(session).list_my_invoices(current_user)


@router.get("/me/invoices/{invoice_id}")
async def download_my_invoice(
    invoice_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    path = await BillingService(session).get_invoice_file(
        user=current_user,
        invoice_id=invoice_id,
    )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
    )


@router.get("/admin/payments", response_model=list[AdminBillingItem])
async def list_admin_payments(
    current_user: Annotated[User, Depends(require_roles("admin", "manager", "staff"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AdminBillingItem]:
    return await BillingService(session).list_admin_billing(current_user)
