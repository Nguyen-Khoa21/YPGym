from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.membership import UserMembership
from app.models.operations import AuditLog
from app.models.user import User
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


async def test_freeze_cancellation_decisions_and_audit_are_persisted(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    async with sessions() as session:
        reviewer = User(name="Manager", email="reviewer@example.com", phone="555123456", role="manager", password_hash="unused", is_email_verified=True)
        session.add(reviewer)
        await session.commit()
    manager = {"Authorization": f"Bearer {create_access_token(user_id=reviewer.id, role='manager', tier='normal')[0]}"}
    request = {"requested_start_date": date.today().isoformat(), "requested_end_date": (date.today() + timedelta(days=7)).isoformat(), "reason": "Travel for the coming week"}
    assert (await client.post("/api/v1/memberships/freeze-requests", headers=headers[0], json={**request, "requested_end_date": (date.today() - timedelta(days=1)).isoformat()})).status_code == 422
    response = await client.post("/api/v1/memberships/freeze-requests", headers=headers[0], json=request)
    assert response.status_code == 200
    request_id = response.json()["id"]
    assert (await client.post("/api/v1/memberships/freeze-requests", headers=headers[0], json=request)).status_code == 409
    assert (await client.get("/api/v1/memberships/requests/me", headers=headers[1])).json() == []
    path = f"/api/v1/admin/freeze-requests/{request_id}/decision"
    decision = {"approve": True, "decision_reason": "Travel request is approved"}
    assert (await client.post(path, headers=headers[0], json=decision)).status_code == 403
    assert (await client.post(path, headers=manager, json=decision)).status_code == 200
    assert (await client.post(path, headers=manager, json=decision)).status_code == 409
    assert (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).status_code == 403
    cancellation = await client.post("/api/v1/memberships/cancellation-requests", headers=headers[0], json={"reason": "Member requests cancellation"})
    assert cancellation.status_code == 200
    path = f"/api/v1/admin/cancellation-requests/{cancellation.json()['id']}/decision"
    assert (await client.post(path, headers=manager, json=decision)).status_code == 422
    decision["outcome"] = "forfeit"
    assert (await client.post(path, headers=manager, json=decision)).status_code == 200
    assert (await client.post(path, headers=manager, json=decision)).status_code == 409
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        assert membership.status == "cancelled" and membership.cancelled_at is not None
        audits = (await session.execute(select(AuditLog).where(AuditLog.target_user_id == users[0].id))).scalars().all()
        assert {item.action for item in audits} == {"membership.freeze.requested", "membership.freeze.approved", "membership.cancellation.requested", "membership.cancellation.approved"}
        assert len(audits) == 4
        approval = next(item for item in audits if item.action == "membership.cancellation.approved")
        assert approval.actor_user_id == reviewer.id and approval.outcome == "forfeit"


async def test_only_admin_can_revoke_and_revocation_blocks_renewal(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    async with sessions() as session:
        admin = User(name="Admin", email="admin-test@example.com", phone="555123456", role="admin", password_hash="unused", is_email_verified=True)
        session.add(admin)
        await session.commit()
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        plan_id = membership.plan_id
    admin_headers = {"Authorization": f"Bearer {create_access_token(user_id=admin.id, role='admin', tier='normal')[0]}"}
    path = f"/api/v1/admin/members/{users[0].id}/revoke"
    body = {"reason": "Documented membership policy breach"}
    assert (await client.post(path, headers=headers[0], json=body)).status_code == 403
    assert (await client.post(path, headers=admin_headers, json=body)).status_code == 200
    assert (await client.post(path, headers=admin_headers, json=body)).status_code == 409
    denied = await client.post("/api/v1/memberships/purchase", headers=headers[0], json={"plan_id": str(plan_id), "idempotency_key": "revoked-purchase", "mock_payment_confirmed": True})
    assert denied.status_code == 403
    async with sessions() as session:
        audits = (await session.execute(select(AuditLog).where(AuditLog.action == "membership.revoked"))).scalars().all()
        assert len(audits) == 1 and audits[0].actor_user_id == admin.id
