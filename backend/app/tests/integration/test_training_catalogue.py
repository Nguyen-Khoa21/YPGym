from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.db import seed
from app.models.operations import AuditLog
from app.models.training import TrainingExercise, TrainingExerciseMuscle
from app.models.user import User
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


async def test_catalogue_roles_filters_archive_and_member_contract(client, storage):
    sessions, _ = storage
    async with sessions() as session:
        users = [User(name=role, email=f"training-{role}@example.com", phone=f"555800{i}", role=role, password_hash="unused", is_email_verified=True) for i, role in enumerate(["member", "staff", "manager", "admin"])]
        session.add_all(users)
        await session.commit()
    headers = {user.role: {"Authorization": f"Bearer {create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]}"} for user in users}
    member_path = "/api/v1/training/exercises"
    admin_path = "/api/v1/admin/training/exercises"
    payload = {"name": "Seated row", "description": "Illustrative cable pulling movement.", "region": "upper", "usage_steps": "Sit upright and pull the handle toward your torso with control.", "safety_note": "Avoid jerking the handle or rounding your back.", "primary_muscles": ["back"], "secondary_muscles": ["biceps"], "is_illustrative": True}
    assert (await client.get(member_path)).status_code == 401
    assert (await client.get(member_path, headers=headers["staff"])).status_code == 403
    assert (await client.post(admin_path, headers=headers["member"], json=payload)).status_code == 403
    assert (await client.post(admin_path, headers=headers["staff"], json=payload)).status_code == 403
    assert (await client.post(admin_path, headers=headers["manager"], json={**payload, "primary_muscles": ["back", "back"]})).status_code == 422
    assert (await client.post(admin_path, headers=headers["manager"], json={**payload, "region": "middle"})).status_code == 422
    created = await client.post(admin_path, headers=headers["manager"], json=payload)
    assert created.status_code == 201, created.text
    item = created.json()
    exercise_id = item["id"]
    assert item["primary_muscles"] == ["back"] and item["has_image"] is False
    listed = await client.get(member_path, headers=headers["member"], params={"region": "upper", "search": "biceps", "muscle": "back"})
    assert listed.status_code == 200 and [row["id"] for row in listed.json()["items"]] == [exercise_id]
    assert (await client.get(f"{member_path}/{exercise_id}", headers=headers["member"])).json()["usage_steps"] == payload["usage_steps"]
    assert (await client.get(member_path, headers=headers["member"], params={"region": "lower"})).json()["page"]["total"] == 0
    assert (await client.get(member_path, headers=headers["member"], params={"muscle": "unknown"})).status_code == 422
    assert (await client.patch(f"{admin_path}/{exercise_id}", headers=headers["manager"], json={"name": None})).status_code == 422
    assert (await client.patch(f"{admin_path}/{exercise_id}", headers=headers["manager"], json={"name": "x"})).status_code == 422
    updated = await client.patch(f"{admin_path}/{exercise_id}", headers=headers["admin"], json={"name": "Seated cable row", "is_active": False})
    assert updated.status_code == 200 and updated.json()["is_active"] is False
    assert (await client.get(f"{member_path}/{exercise_id}", headers=headers["member"])).status_code == 404
    assert (await client.get(member_path, headers=headers["member"])).json()["page"]["total"] == 0
    assert (await client.get(admin_path, headers=headers["manager"])).json()["items"][0]["name"] == "Seated cable row"
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(TrainingExercise)) == 1
        assert await session.scalar(select(func.count()).select_from(TrainingExerciseMuscle)) == 2
        assert await session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == exercise_id)) == 2


async def test_catalogue_image_is_validated_reencoded_and_role_protected(client, storage):
    sessions, _ = storage
    async with sessions() as session:
        users = [User(name=role, email=f"training-image-{role}@example.com", phone=f"555900{i}", role=role, password_hash="unused", is_email_verified=True) for i, role in enumerate(["member", "manager"])]
        session.add_all(users)
        await session.commit()
    headers = {user.role: {"Authorization": f"Bearer {create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]}"} for user in users}
    payload = {"name": "Step-up", "description": "Illustrative lower body movement.", "region": "lower", "usage_steps": "Step onto a stable platform and lower back down slowly.", "safety_note": "Use a stable, suitable-height platform and keep your balance.", "primary_muscles": ["quadriceps"], "secondary_muscles": ["glutes"]}
    exercise_id = (await client.post("/api/v1/admin/training/exercises", headers=headers["manager"], json=payload)).json()["id"]
    url = f"/api/v1/admin/training/exercises/{exercise_id}/image"
    assert (await client.put(url, headers=headers["member"], files={"file": ("fake.png", b"not-an-image", "image/png")})).status_code == 403
    assert (await client.put(url, headers=headers["manager"], files={"file": ("fake.png", b"not-an-image", "image/png")})).status_code == 422
    assert (await client.put(url, headers=headers["manager"], files={"file": ("large.png", b"x" * 2_000_001, "image/png")})).status_code == 422
    buffer = BytesIO()
    Image.new("RGB", (12, 12), "green").save(buffer, format="PNG")
    uploaded = await client.put(url, headers=headers["manager"], files={"file": ("sample.png", buffer.getvalue(), "image/png")})
    assert uploaded.status_code == 200 and uploaded.json()["has_image"] is True
    served = await client.get(f"/api/v1/training/exercises/{exercise_id}/image")
    assert served.status_code == 200 and served.headers["content-type"] == "image/jpeg" and served.content.startswith(b"\xff\xd8")
    assert buffer.getvalue() not in served.content


async def test_catalogue_seed_is_illustrative_idempotent_and_preserves_admin_edits(storage, monkeypatch):
    sessions, _ = storage
    monkeypatch.setattr(seed, "AsyncSessionLocal", sessions)
    await seed.seed_development_data()
    async with sessions() as session:
        rows = (await session.scalars(select(TrainingExercise))).all()
        assert len(rows) == 4 and all(row.is_illustrative for row in rows)
        rows[0].name = "Edited by manager"
        await session.commit()
    await seed.seed_development_data()
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(TrainingExercise)) == 4
        assert await session.scalar(select(func.count()).select_from(TrainingExercise).where(TrainingExercise.name == "Edited by manager")) == 1
