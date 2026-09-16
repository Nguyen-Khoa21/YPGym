import csv
import io
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.operations import AuditLog
from app.models.system_configuration import SystemConfiguration
from app.models.user import User
from app.services.configuration_service import ConfigurationService
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


async def operational_roles(sessions):
    async with sessions() as session:
        users = [User(name=f"{role} reviewer", email=f"{role}@example.com", phone=f"5550000{i}",
                      role=role, password_hash="unused", is_email_verified=True)
                 for i, role in enumerate(["admin", "manager", "staff", "pt"])]
        session.add_all(users)
        await session.commit()
    return {user.role: {"Authorization": f"Bearer {create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]}"} for user in users}


async def test_configuration_permissions_bounds_cache_and_audit(client, storage, eligible_members):
    sessions, redis = storage
    _, member_headers = eligible_members
    roles = await operational_roles(sessions)
    async with sessions() as session:
        session.add(SystemConfiguration(key="gym_capacity", value="150", value_type="integer", description="Integration capacity"))
        await session.commit()
        assert await ConfigurationService(session, redis).get_int("gym_capacity") == 150
    assert await redis.get("ypgym:config:gym_capacity") == "150"
    assert 0 < await redis.ttl("ypgym:config:gym_capacity") <= 300
    path = "/api/v1/admin/configuration/gym_capacity"
    assert (await client.patch(path, json={"value": 151})).status_code == 401
    for headers in [member_headers[0], roles["staff"], roles["pt"]]:
        assert (await client.get("/api/v1/admin/configuration", headers=headers)).status_code == 403
        assert (await client.patch(path, headers=headers, json={"value": 151})).status_code == 403
    for role in ["manager", "admin"]:
        assert (await client.get("/api/v1/admin/configuration", headers=roles[role])).status_code == 200
        for value in [0, 5001, "invalid", 1.5]:
            assert (await client.patch(path, headers=roles[role], json={"value": value})).status_code == 422
    assert (await client.patch("/api/v1/admin/configuration/unknown", headers=roles["admin"], json={"value": 10})).status_code == 404
    assert (await client.patch(path, headers=roles["manager"], json={"value": 200})).status_code == 200
    assert await redis.get("ypgym:config:gym_capacity") is None
    async with sessions() as session:
        assert await ConfigurationService(session, redis).get_int("gym_capacity") == 200
        record = (await session.scalars(select(SystemConfiguration))).one()
        assert record.value == "200"
        audits = (await session.scalars(select(AuditLog))).all()
        assert len(audits) == 1 and audits[0].action == "configuration.updated"
        assert audits[0].before_data == {"key": "gym_capacity", "value": 150}
        assert audits[0].after_data == {"key": "gym_capacity", "value": 200}
    assert await redis.get("ypgym:config:gym_capacity") == "200"


async def test_filtered_csv_permissions_formula_safety_and_export_audits(client, storage, eligible_members):
    sessions, _ = storage
    users, member_headers = eligible_members
    roles = await operational_roles(sessions)
    hostile_name = "\t=HYPERLINK(\"https://example.invalid\",\"untrusted\")"
    async with sessions() as session:
        user = await session.get(User, users[0].id)
        user.name = hostile_name
        await session.commit()
    crm_filters = {"search": users[0].email, "role": "member", "tier": "normal", "status": "active", "expiry_from": date.today().isoformat(), "expiry_to": (date.today() + timedelta(days=31)).isoformat(), "sort_by": "email", "sort_order": "asc"}
    paths = ["/api/v1/admin/members/export.csv", "/api/v1/admin/billing/payments/export.csv", "/api/v1/admin/billing/invoices/export.csv"]
    for path in paths:
        assert (await client.get(path)).status_code == 401
        for headers in [member_headers[0], roles["manager"], roles["staff"], roles["pt"]]:
            assert (await client.get(path, headers=headers)).status_code == 403
    table = await client.get("/api/v1/admin/members", params=crm_filters, headers=roles["admin"])
    response = await client.get(paths[0], params=crm_filters, headers=roles["admin"])
    assert table.status_code == response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [row["Member ID"] for row in rows] == [item["id"] for item in table.json()["items"]]
    assert len(rows) == 1 and rows[0]["Name"] == "'" + hostile_name
    assert "attachment" in response.headers["content-disposition"]
    assert "password_hash" not in response.text
    async with sessions() as session:
        from app.models.membership import UserMembership
        plan_id = await session.scalar(select(UserMembership.plan_id).where(UserMembership.user_id == users[0].id))
    purchase = await client.post("/api/v1/memberships/purchase", headers=member_headers[0], json={"plan_id": str(plan_id), "idempotency_key": "csv-integration-purchase", "mock_payment_confirmed": True})
    assert purchase.status_code == 200
    filters = {"member": users[0].email, "status": "succeeded", "plan": "Integration monthly", "tier": "normal"}
    for kind in ["payments", "invoices"]:
        table = await client.get(f"/api/v1/admin/billing/{kind}", headers=roles["admin"], params=filters)
        exported = await client.get(f"/api/v1/admin/billing/{kind}/export.csv", headers=roles["admin"], params=filters)
        assert table.status_code == exported.status_code == 200
        rows = list(csv.DictReader(io.StringIO(exported.text)))
        id_key = "Payment ID" if kind == "payments" else "Invoice ID"
        assert [row[id_key] for row in rows] == [item[f"{kind[:-1]}_id"] for item in table.json()["items"]]
        assert len(rows) == 1 and rows[0]["Member"] == "'" + hostile_name
        assert rows[0]["Amount"] == "720000.00"
        empty = await client.get(f"/api/v1/admin/billing/{kind}/export.csv", headers=roles["admin"], params={**filters, "member": users[1].email})
        assert list(csv.DictReader(io.StringIO(empty.text))) == []
    async with sessions() as session:
        audits = (await session.scalars(select(AuditLog).where(AuditLog.action.like("%exported")))).all()
        assert len(audits) == 5
        assert {item.action for item in audits} == {"crm.members.exported", "billing.payments.exported", "billing.invoices.exported"}
        assert sorted(item.outcome for item in audits) == ["0 rows", "0 rows", "1 rows", "1 rows", "1 rows"]
