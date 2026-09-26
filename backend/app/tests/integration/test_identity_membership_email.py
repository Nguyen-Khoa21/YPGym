from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser
from mailbox import Maildir
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from app.models.email_delivery import EmailDelivery
from app.models.identity import ExternalIdentity
from app.models.membership import UserMembership
from app.models.user import User
from app.services.email_service import EmailDeliveryService
from app.services.oauth_service import ProviderProfile
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


async def test_google_login_uses_single_use_state_and_exchange_without_email_merge(client, storage, monkeypatch):
    sessions, _redis = storage
    monkeypatch.setattr("app.services.oauth_service.OAuthService._configured", lambda self, provider: True)

    async def profile(*args, **kwargs):
        return ProviderProfile(subject="google-subject-1", email="social@example.com", name="Social member", email_verified=True)

    monkeypatch.setattr("app.services.oauth_service.OAuthProviderClient.validate", profile)
    started = await client.get("/api/v1/auth/oauth/google/start", params={"platform": "web"})
    assert started.status_code == 200
    state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
    callback = await client.get(
        "/api/v1/auth/oauth/google/callback",
        params={"state": state, "code": "provider-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    callback_query = parse_qs(urlsplit(callback.headers["location"]).query)
    exchange = await client.post(
        "/api/v1/auth/oauth/google/exchange",
        json={"code": callback_query["code"][0]},
    )
    assert exchange.status_code == 200
    assert exchange.json()["user"]["role"] == "member"
    assert exchange.json()["user"]["is_email_verified"] is True
    assert (await client.post("/api/v1/auth/oauth/google/exchange", json={"code": callback_query["code"][0]})).status_code == 401
    auth_headers = {"Authorization": f"Bearer {exchange.json()['access_token']}"}
    assert (await client.get("/api/v1/account/identities", headers=auth_headers)).json()["identities"][0]["provider"] == "google"
    assert (await client.delete("/api/v1/account/identities/google", headers=auth_headers)).status_code == 409
    replay = await client.get(
        "/api/v1/auth/oauth/google/callback",
        params={"state": state, "code": "provider-code"},
        follow_redirects=False,
    )
    assert "invalid_or_expired_state" in replay.headers["location"]
    async with sessions() as session:
        assert int((await session.execute(select(func.count(User.id)))).scalar_one()) == 1
        identity = (await session.execute(select(ExternalIdentity))).scalar_one()
        assert identity.provider_subject == "google-subject-1"
        assert identity.provider_email == "social@example.com"


async def test_existing_email_requires_explicit_link(client, storage, monkeypatch):
    sessions, _redis = storage
    async with sessions() as session:
        existing_user = User(name="Existing", email="existing-social@example.com", phone="123456789", password_hash="unused", is_email_verified=True)
        session.add(existing_user)
        await session.commit()
    monkeypatch.setattr("app.services.oauth_service.OAuthService._configured", lambda self, provider: True)

    async def profile(*args, **kwargs):
        return ProviderProfile(subject="facebook-subject-1", email="existing-social@example.com", name="Existing", email_verified=False)

    monkeypatch.setattr("app.services.oauth_service.OAuthProviderClient.validate", profile)
    started = await client.get("/api/v1/auth/oauth/facebook/start")
    state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
    callback = await client.get("/api/v1/auth/oauth/facebook/callback", params={"state": state, "code": "code"}, follow_redirects=False)
    assert "account_link_required" in callback.headers["location"]
    headers = {"Authorization": f"Bearer {create_access_token(user_id=existing_user.id, role='member', tier='normal')[0]}"}
    link_start = await client.post("/api/v1/account/identities/facebook/link/start", headers=headers)
    assert link_start.status_code == 200
    link_state = parse_qs(urlsplit(link_start.json()["authorization_url"]).query)["state"][0]
    linked = await client.get("/api/v1/auth/oauth/facebook/callback", params={"state": link_state, "code": "link-code"}, follow_redirects=False)
    assert "/app/security?linked=facebook" in linked.headers["location"]
    async with sessions() as session:
        assert int((await session.execute(select(func.count(ExternalIdentity.id)))).scalar_one()) == 1


async def test_purchase_queues_two_idempotent_messages_and_worker_attaches_invoice(client, storage, eligible_members, tmp_path):
    sessions, _redis = storage
    users, headers = eligible_members
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        plan_id = membership.plan_id
    payload = {"plan_id": str(plan_id), "idempotency_key": "email-outbox-purchase-1", "mock_payment_confirmed": True}
    purchased = await client.post("/api/v1/memberships/purchase", headers=headers[0], json=payload)
    assert purchased.status_code == 200
    assert (await client.post("/api/v1/memberships/purchase", headers=headers[0], json=payload)).status_code == 200
    async with sessions() as session:
        queued = list((await session.execute(select(EmailDelivery).order_by(EmailDelivery.template_type))).scalars())
        assert [item.template_type for item in queued] == ["membership_invoice", "membership_renewal"]
        assert all(item.status == "queued" and item.attempt_count == 0 for item in queued)
        settings = SimpleNamespace(
            EMAIL_DELIVERY_MODE="development", EMAIL_DELIVERY_BATCH_SIZE=25,
            EMAIL_MAX_DELIVERY_ATTEMPTS=5, EMAIL_RETRY_DELAY_SECONDS=1,
            EMAIL_SENDER_NAME="YPGym Team", EMAIL_SENDER_ADDRESS="no-reply@example.com",
            EMAIL_REPLY_TO="support@example.com", FRONTEND_URL="http://frontend.test",
            DEVELOPMENT_MAIL_DIR=str(tmp_path / "mail"),
        )
        service = EmailDeliveryService(session, settings=settings)
        assert await service.deliver_pending_membership_emails() == 2
        assert await service.deliver_pending_membership_emails() == 0
        delivered = list((await session.execute(select(EmailDelivery))).scalars())
        assert all(item.status == "sent_to_provider" and item.attempt_count == 1 for item in delivered)
    outbox = Maildir(tmp_path / "mail", create=False)
    try:
        messages = [BytesParser(policy=policy.default).parsebytes(item.as_bytes()) for item in outbox.values()]
        assert len(messages) == 2
        assert all(message["To"] == users[0].email for message in messages)
        invoice_message = next(message for message in messages if message["Subject"].startswith("YPGym invoice"))
        assert any(part.get_content_type() == "application/pdf" for part in invoice_message.walk())
        assert "VND" in invoice_message.get_body(preferencelist=("plain",)).get_content()
    finally:
        outbox.close()


async def test_manager_can_list_and_retry_only_failed_delivery(client, storage, eligible_members):
    sessions, _redis = storage
    users, member_headers = eligible_members
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        plan_id = membership.plan_id
    purchase = await client.post(
        "/api/v1/memberships/purchase",
        headers=member_headers[0],
        json={"plan_id": str(plan_id), "idempotency_key": "manager-email-retry", "mock_payment_confirmed": True},
    )
    assert purchase.status_code == 200
    async with sessions() as session:
        manager = User(name="Manager", email="email-manager@example.com", phone="5559911", role="manager", password_hash="unused", is_email_verified=True)
        session.add(manager)
        await session.commit()
        delivery = (await session.execute(select(EmailDelivery).where(EmailDelivery.template_type == "membership_invoice"))).scalar_one()
        delivery.status = "failed"
        await session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user_id=manager.id, role='manager', tier='normal')[0]}"}
    listed = await client.get("/api/v1/admin/email-deliveries", headers=headers, params={"status": "failed"})
    assert listed.status_code == 200
    delivery_id = listed.json()["items"][0]["id"]
    retried = await client.post(f"/api/v1/admin/email-deliveries/{delivery_id}/retry", headers=headers)
    assert retried.status_code == 200 and retried.json()["delivery"]["status"] == "queued"
    assert (await client.post(f"/api/v1/admin/email-deliveries/{delivery_id}/retry", headers=headers)).status_code == 409


async def test_stale_email_claim_stops_at_retry_limit(client, storage, eligible_members):
    sessions, _redis = storage
    users, headers = eligible_members
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        plan_id = membership.plan_id
    purchased = await client.post(
        "/api/v1/memberships/purchase",
        headers=headers[0],
        json={"plan_id": str(plan_id), "idempotency_key": "stale-email-claim", "mock_payment_confirmed": True},
    )
    assert purchased.status_code == 200
    async with sessions() as session:
        deliveries = list((await session.execute(select(EmailDelivery).order_by(EmailDelivery.template_type))).scalars())
        deliveries[0].status = "sending"
        deliveries[0].attempt_count = 2
        deliveries[0].last_attempt_at = datetime.now(UTC) - timedelta(minutes=20)
        deliveries[1].status = "sent_to_provider"
        await session.commit()
        service = EmailDeliveryService(session)
        assert await service.deliveries.claim_next(max_attempts=2) is None
        await session.commit()
        exhausted = await session.get(EmailDelivery, deliveries[0].id)
        assert exhausted.status == "failed"
        assert exhausted.attempt_count == 2
        assert exhausted.last_error_code == "stale_claim_exhausted"
