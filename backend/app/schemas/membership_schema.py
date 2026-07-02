from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MembershipPlanResponse(BaseModel):
    id: UUID
    name: str
    duration_months: int
    duration_days: int
    base_price: Decimal
    discount_percent: Decimal
    final_price: Decimal
    is_active: bool
    tier_availability: str | None
    benefits: list[str]


class MembershipSummary(BaseModel):
    id: UUID
    plan_id: UUID
    plan_name: str
    status: str
    start_date: date
    expiry_date: date


class PurchaseMembershipRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=120)
    mock_payment_confirmed: bool


class PaymentSummary(BaseModel):
    id: UUID
    amount: Decimal
    discount_amount: Decimal
    status: str
    mock_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceSummary(BaseModel):
    id: UUID
    invoice_number: str
    amount: Decimal
    discount_amount: Decimal
    transaction_date: datetime
    membership_start_date: date
    membership_expiry_date: date
    download_url: str


class PurchaseMembershipResponse(BaseModel):
    message: str
    membership: MembershipSummary
    payment: PaymentSummary
    invoice: InvoiceSummary
