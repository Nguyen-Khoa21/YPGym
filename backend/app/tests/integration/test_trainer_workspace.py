from datetime import UTC, datetime, timedelta

import pytest

from app.models.classes import GymClass, PersonalTrainer
from app.models.user import User
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


async def test_trainer_workspace_is_owned_bounded_and_role_protected(client, storage):
    sessions, _ = storage
    now = datetime.now(UTC)
    async with sessions() as session:
        users = [User(name=f"{role} trainer reviewer", email=f"workspace{i}@example.com",
                      phone=f"5555000{i}", role=role, password_hash="unused", is_email_verified=True)
                 for i, role in enumerate(["pt", "pt", "pt", "member", "staff", "manager", "admin"])]
        session.add_all(users)
        await session.flush()
        own = PersonalTrainer(user_id=users[0].id, display_name="Own coach", bio="Own public bio", is_active=True)
        other = PersonalTrainer(user_id=users[1].id, display_name="Other coach", is_active=True)
        session.add_all([own, other])
        await session.flush()
        for i, (trainer, days, status) in enumerate([
            *[(own, day, "scheduled") for day in [4, 2, 1, 3]],
            (own, -1, "scheduled"), (own, 1, "cancelled"), (other, 1, "scheduled"),
        ]):
            start = now + timedelta(days=days)
            session.add(GymClass(title=f"Workspace class {i}", class_type="Strength", start_at=start,
                                 end_at=start + timedelta(hours=1), capacity=10, trainer_id=trainer.id,
                                 location="Studio A", status=status))
        await session.commit()
    headers = [{"Authorization": f"Bearer {create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]}"}
               for user in users]
    path = "/api/v1/trainers/me"
    assert (await client.get(path)).status_code == 401
    for denied in headers[3:]:
        assert (await client.get(path, headers=denied)).status_code == 403
    assert (await client.get(path, headers=headers[2])).status_code == 404
    response = await client.get(path, headers=headers[0], params={"user_id": str(users[1].id), "trainer_id": str(other.id)})
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == str(own.id) and result["bio"] == "Own public bio"
    assert [item["title"] for item in result["upcoming_classes"]] == ["Workspace class 2", "Workspace class 1", "Workspace class 3"]
    assert "user_id" not in result and "password_hash" not in result
    assert (await client.get(f"/api/v1/trainers/{other.id}")).status_code == 200
    async with sessions() as session:
        trainer = await session.get(PersonalTrainer, own.id)
        trainer.is_active = False
        await session.commit()
    assert (await client.get(path, headers=headers[0])).json()["is_active"] is False
    assert (await client.get(f"/api/v1/trainers/{own.id}")).status_code == 404
