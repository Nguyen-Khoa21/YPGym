from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models.auth_token import EmailVerification, PasswordReset
from app.models.billing import Invoice, Payment
from app.models.membership import MembershipPlan
from app.models.user import User
from app.utils.security import create_access_token, hash_token

pytestmark = pytest.mark.asyncio


async def test_registration_verification_login_and_one_time_reset(client, storage, monkeypatch):
    sessions, _ = storage
    verification = "test-verification-material-123456"
    reset = "test-reset-material-1234567890123"
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: verification)
    payload = {"name": "Test member", "email": "journey@example.com", "phone": "123456789", "password": "Test-password-123"}
    registered = await client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    assert "password" not in registered.text and verification not in registered.text
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409
    assert (await client.post("/api/v1/auth/register", json={**payload, "email": "second@example.com"})).status_code == 409
    credentials = {"email": payload["email"], "password": payload["password"]}
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 403
    async with sessions() as session:
        row = (await session.execute(select(EmailVerification))).scalar_one()
        assert row.token_hash == hash_token(verification)
    assert (await client.get("/api/v1/auth/verify-email", params={"token": verification})).status_code == 200
    login = await client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["email"] == payload["email"]
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: reset)
    existing = await client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})
    missing = await client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert existing.json() == missing.json()
    async with sessions() as session:
        record = (await session.execute(select(PasswordReset))).scalar_one()
        assert record.token_hash == hash_token(reset)
    reset_payload = {"token": reset, "new_password": "New-test-password-123"}
    assert (await client.post("/api/v1/auth/reset-password", json=reset_payload)).status_code == 200
    assert (await client.post("/api/v1/auth/reset-password", json=reset_payload)).status_code == 400
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={**credentials, "password": reset_payload["new_password"]})).status_code == 200


async def test_purchase_renewal_idempotency_invoice_and_ownership(client, storage):
    sessions, _ = storage
    async with sessions() as session:
        user = User(name="Buyer", email="buyer@example.com", phone="123456789", password_hash="unused", is_email_verified=True)
        other = User(name="Other", email="other@example.com", phone="987654321", password_hash="unused", is_email_verified=True)
        plan = MembershipPlan(name="Test monthly", duration_months=1, duration_days=30, base_price=Decimal("720000"), discount_percent=Decimal("5"))
        session.add_all([user, other, plan])
        await session.commit()
    token, _ = create_access_token(user_id=user.id, role="member", tier="normal")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"plan_id": str(plan.id), "idempotency_key": "purchase-test-1", "mock_payment_confirmed": False}
    assert (await client.post("/api/v1/memberships/purchase", json=payload, headers=headers)).status_code == 400
    payload["mock_payment_confirmed"] = True
    response = await client.post("/api/v1/memberships/purchase", json=payload, headers=headers)
    assert response.status_code == 200
    first = response.json()
    assert Decimal(first["payment"]["amount"]) == Decimal("684000")
    duplicate = (await client.post("/api/v1/memberships/purchase", json=payload, headers=headers)).json()
    assert duplicate["payment"]["id"] == first["payment"]["id"]
    renewal = (await client.post("/api/v1/memberships/purchase", json={**payload, "idempotency_key": "purchase-test-2"}, headers=headers)).json()
    assert date.fromisoformat(renewal["membership"]["expiry_date"]) == date.fromisoformat(first["membership"]["expiry_date"]) + timedelta(days=30)
    invoice_path = first["invoice"]["download_url"]
    pdf = await client.get(invoice_path, headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    other_token, _ = create_access_token(user_id=other.id, role="member", tier="normal")
    assert (await client.get(invoice_path, headers={"Authorization": f"Bearer {other_token}"})).status_code == 404
    async with sessions() as session:
        assert (await session.execute(select(func.count(Payment.id)))).scalar_one() == 2
        assert (await session.execute(select(func.count(Invoice.id)))).scalar_one() == 2
        invoice = await session.get(Invoice, UUID(first["invoice"]["id"]))
        assert invoice.membership_expiry_date == date.fromisoformat(first["membership"]["expiry_date"])
