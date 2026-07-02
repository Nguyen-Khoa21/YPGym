from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PaymentHistoryItem(BaseModel):
    id: UUID
    plan_name: str
    amount: Decimal
    discount_amount: Decimal
    status: str
    mock_reference: str
    created_at: datetime


class InvoiceHistoryItem(BaseModel):
    id: UUID
    invoice_number: str
    plan_name: str
    amount: Decimal
    discount_amount: Decimal
    transaction_date: datetime
    membership_start_date: date
    membership_expiry_date: date
    download_url: str


class AdminBillingItem(BaseModel):
    payment_id: UUID
    user_id: UUID
    member_name: str
    member_email: str
    plan_name: str
    amount: Decimal
    status: str
    created_at: datetime
