"""Invoice PDF download: stored file reuse, regeneration, safe failures and ownership."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.models.billing import Invoice, Payment
from app.models.membership import MembershipPlan
from app.models.user import User
from app.services.invoice_service import InvoicePdfService
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id, role='member', tier='normal')[0]}"}


@pytest.fixture
def storage_dir(tmp_path, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "INVOICE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.invoice_service.get_settings", lambda: settings)
    return tmp_path


async def seed_invoice(storage, *, product_type: str = "membership", pdf_path: str = "missing.pdf"):
    sessions, _ = storage
    now = datetime.now(UTC)
    async with sessions() as session:
        plan = MembershipPlan(name=f"Invoice plan {uuid4().hex[:6]}", duration_months=1, duration_days=30, base_price=Decimal("720000"))
        member = User(name="Invoice Member", email=f"inv-{uuid4().hex[:8]}@example.com", password_hash="unused", is_email_verified=True)
        other = User(name="Other Member", email=f"inv-o-{uuid4().hex[:8]}@example.com", password_hash="unused", is_email_verified=True)
        session.add_all([plan, member, other])
        await session.flush()
        payment = Payment(
            user_id=member.id, plan_id=plan.id, amount=Decimal("720000"), amount_vnd=720000, discount_amount=0,
            status="succeeded", idempotency_key=f"inv-{uuid4().hex}", mock_reference=f"inv-{uuid4().hex}",
        )
        session.add(payment)
        await session.flush()
        is_class = product_type == "class_booking"
        invoice = Invoice(
            invoice_number=f"YPG-TEST-{uuid4().hex[:8].upper()}", user_id=member.id, payment_id=payment.id,
            product_type=product_type, product_name="Invoice product", plan_name=plan.name,
            amount=Decimal("720000"), discount_amount=Decimal("0"), transaction_date=now,
            membership_start_date=None if is_class else date.today(),
            membership_expiry_date=None if is_class else date.today() + timedelta(days=30),
            service_start_at=now if is_class else None,
            service_end_at=now + timedelta(hours=1) if is_class else None,
            pdf_path=pdf_path,
        )
        session.add(invoice)
        await session.commit()
        return member, other, invoice


@pytest.mark.parametrize("product_type", ["membership", "class_booking"])
async def test_missing_stored_pdf_is_regenerated_for_both_product_types(client, storage, storage_dir, product_type):
    member, _, invoice = await seed_invoice(storage, product_type=product_type)
    response = await client.get(f"/api/v1/billing/me/invoices/{invoice.id}", headers=auth(member))
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert response.headers["cache-control"] == "private, no-store"
    assert not list(Path(storage_dir).glob(".*.tmp")), "temporary render files must not be left behind"


async def test_stored_pdf_is_served_without_regeneration(client, storage, storage_dir, monkeypatch):
    stored = storage_dir / "stored.pdf"
    stored.write_bytes(b"%PDF-1.4 stored invoice")
    member, _, invoice = await seed_invoice(storage, pdf_path=str(stored))

    def fail(*args, **kwargs):
        raise AssertionError("must not regenerate when a stored PDF exists")

    monkeypatch.setattr(InvoicePdfService, "generate_pdf", fail)
    response = await client.get(f"/api/v1/billing/me/invoices/{invoice.id}", headers=auth(member))
    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 stored invoice"


async def test_pdf_outside_storage_dir_is_never_served(client, storage, storage_dir, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.pdf"
    outside.write_bytes(b"%PDF-1.4 secret")
    member, _, invoice = await seed_invoice(storage, pdf_path=str(outside))
    response = await client.get(f"/api/v1/billing/me/invoices/{invoice.id}", headers=auth(member))
    assert response.status_code == 200
    assert b"secret" not in response.content


async def test_render_failure_returns_safe_503_without_internals(client, storage, storage_dir, monkeypatch):
    member, _, invoice = await seed_invoice(storage)

    def boom(self, **kwargs):
        raise OSError(f"disk full at {storage_dir}")

    monkeypatch.setattr(InvoicePdfService, "generate_pdf", boom)
    response = await client.get(f"/api/v1/billing/me/invoices/{invoice.id}", headers=auth(member))
    assert response.status_code == 503
    body = response.text
    assert "INVOICE_PDF_UNAVAILABLE" in body
    assert str(storage_dir) not in body and "disk full" not in body


async def test_other_member_and_anonymous_cannot_download(client, storage, storage_dir):
    _, other, invoice = await seed_invoice(storage)
    assert (await client.get(f"/api/v1/billing/me/invoices/{invoice.id}", headers=auth(other))).status_code == 404
    assert (await client.get(f"/api/v1/billing/me/invoices/{invoice.id}")).status_code == 401


async def test_failed_render_leaves_no_partial_file(storage_dir, monkeypatch):
    service = InvoicePdfService()
    monkeypatch.setattr("reportlab.pdfgen.canvas.Canvas.save", lambda self: (_ for _ in ()).throw(RuntimeError("render failed")))
    with pytest.raises(RuntimeError):
        service.generate_pdf(
            invoice_number="YPG-ATOMIC", member_name="A", member_email="a@example.com", plan_name="P",
            amount=Decimal("1"), discount_amount=Decimal("0"), transaction_date=datetime.now(UTC),
            membership_start_date=date.today(), membership_expiry_date=date.today(),
        )
    assert list(Path(storage_dir).iterdir()) == []


async def test_resolve_stored_pdf_rejects_empty_missing_and_foreign_files(storage_dir, tmp_path_factory):
    service = InvoicePdfService()
    empty = storage_dir / "empty.pdf"
    empty.write_bytes(b"")
    foreign = tmp_path_factory.mktemp("foreign") / "x.pdf"
    foreign.write_bytes(b"%PDF")
    good = storage_dir / "good.pdf"
    good.write_bytes(b"%PDF")
    assert service.resolve_stored_pdf(None) is None
    assert service.resolve_stored_pdf(str(empty)) is None
    assert service.resolve_stored_pdf(str(storage_dir / "nope.pdf")) is None
    assert service.resolve_stored_pdf(str(foreign)) is None
    assert service.resolve_stored_pdf(str(good)) == good.resolve()
