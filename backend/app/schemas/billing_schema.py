from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.membership_schema import AttendanceBenefitQuote


class PaymentHistoryItem(BaseModel):
    id: UUID
    product_type: str
    product_name: str
    class_booking_id: UUID | None
    plan_name: str
    amount: Decimal
    discount_amount: Decimal
    status: str
    mock_reference: str
    provider: str
    reference: str
    paid_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    discount_details: AttendanceBenefitQuote | None


class InvoiceHistoryItem(BaseModel):
    id: UUID
    invoice_number: str
    plan_name: str
    product_type: str
    product_name: str
    class_booking_id: UUID | None
    amount: Decimal
    discount_amount: Decimal
    transaction_date: datetime
    membership_start_date: date | None
    membership_expiry_date: date | None
    service_start_at: datetime | None
    service_end_at: datetime | None
    download_url: str
    discount_details: AttendanceBenefitQuote | None


class AdminBillingItem(BaseModel):
    payment_id: UUID
    user_id: UUID
    member_name: str
    member_email: str
    plan_name: str
    product_type: str
    product_name: str
    class_booking_id: UUID | None
    invoice_id: UUID | None
    provider_reference: str
    refund_status: str | None
    amount: Decimal
    status: str
    created_at: datetime
