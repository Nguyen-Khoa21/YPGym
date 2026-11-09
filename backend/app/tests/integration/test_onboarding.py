from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, GymLocation, WorkforceGymAssignment
from app.models.onboarding import MemberOnboardingProfile
from app.models.user import User
from app.utils.security import create_access_token


pytestmark = pytest.mark.asyncio

ANSWERS = {"is_new_to_gym": True, "prefers_uncrowded_hours": True, "closer_gym_id": str(DISTRICT_11_GYM_ID)}


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]
    return {"Authorization": f"Bearer {token}"}


async def make_user(sessions, role: str, email: str, gym_id=None) -> User:
    async with sessions() as session:
        user = User(name=email.split("@")[0], email=email, role=role, password_hash="unused", is_email_verified=True)
        session.add(user)
        await session.flush()
        if gym_id:
            session.add(WorkforceGymAssignment(user_id=user.id, gym_id=gym_id, assigned_role=role))
        await session.commit()
        await session.refresh(user)
        return user


async def test_member_questionnaire_lifecycle(client, storage):
    sessions, _ = storage
    member = await make_user(sessions, "member", "onb-member@example.com")
    headers = auth_header(member)

    first = await client.get("/api/v1/users/me/onboarding", headers=headers)
    assert first.json()["status"] == "not_started"

    partial = await client.put("/api/v1/users/me/onboarding", headers=headers, json={"is_new_to_gym": True})
    assert partial.json()["status"] == "partial"

    done = await client.put("/api/v1/users/me/onboarding", headers=headers, json={**ANSWERS, "main_goal": "stamina"})
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "complete"
    assert done.json()["completed_at"] is not None

    skipped_later = await client.post("/api/v1/users/me/onboarding/skip", headers=headers)
    assert skipped_later.json()["status"] == "complete"


async def test_skip_is_remembered_and_unanswered_gives_no_recommendation(client, storage):
    sessions, _ = storage
    member = await make_user(sessions, "member", "onb-skip@example.com")
    headers = auth_header(member)
    skipped = await client.post("/api/v1/users/me/onboarding/skip", headers=headers)
    assert skipped.json()["status"] == "skipped"
    recommendations = await client.get("/api/v1/users/me/recommendations", headers=headers)
    assert recommendations.status_code == 200
    assert recommendations.json() == {}


async def test_answers_are_validated(client, storage):
    sessions, _ = storage
    member = await make_user(sessions, "member", "onb-validate@example.com")
    headers = auth_header(member)
    unknown = await client.put("/api/v1/users/me/onboarding", headers=headers, json={"closer_gym_id": str(uuid4())})
    assert unknown.status_code == 422
    async with sessions() as session:
        gym = await session.get(GymLocation, DISTRICT_11_GYM_ID)
        gym.is_active = False
        await session.commit()
    inactive = await client.put("/api/v1/users/me/onboarding", headers=headers, json=ANSWERS)
    assert inactive.status_code == 422
    bad_choice = await client.put("/api/v1/users/me/onboarding", headers=headers, json={"main_goal": "fly"})
    assert bad_choice.status_code == 422
    extra = await client.put("/api/v1/users/me/onboarding", headers=headers, json={"user_id": str(uuid4())})
    assert extra.status_code == 422


async def test_recommendations_follow_answers(client, storage):
    sessions, _ = storage
    member = await make_user(sessions, "member", "onb-reco@example.com")
    headers = auth_header(member)
    await client.put("/api/v1/users/me/onboarding", headers=headers, json=ANSWERS)
    body = (await client.get("/api/v1/users/me/recommendations", headers=headers)).json()
    assert body["recommended_gym"]["id"] == str(DISTRICT_11_GYM_ID)
    # No attendance history in the test database: never invent quiet hours.
    assert "quiet_hours" not in body
    assert body["quiet_hours_reason"] == "not_enough_data"

    await client.put("/api/v1/users/me/onboarding", headers=headers, json={**ANSWERS, "prefers_uncrowded_hours": False})
    body = (await client.get("/api/v1/users/me/recommendations", headers=headers)).json()
    assert "quiet_hours" not in body and "quiet_hours_reason" not in body
    assert body["recommended_gym"]["id"] == str(DISTRICT_11_GYM_ID)


async def test_members_only_and_no_cross_member_access(client, storage):
    sessions, _ = storage
    staff = await make_user(sessions, "staff", "onb-staff@example.com", DISTRICT_1_GYM_ID)
    assert (await client.get("/api/v1/users/me/onboarding", headers=auth_header(staff))).status_code == 403
    assert (await client.get("/api/v1/users/me/recommendations", headers=auth_header(staff))).status_code == 403
    one = await make_user(sessions, "member", "onb-a@example.com")
    two = await make_user(sessions, "member", "onb-b@example.com")
    await client.put("/api/v1/users/me/onboarding", headers=auth_header(one), json=ANSWERS)
    assert (await client.get("/api/v1/users/me/onboarding", headers=auth_header(two))).json()["status"] == "not_started"


async def test_insights_scope_and_small_group_suppression(client, storage):
    sessions, _ = storage
    owner = await make_user(sessions, "admin", "onb-owner@example.com")
    manager_1 = await make_user(sessions, "manager", "onb-m1@example.com", DISTRICT_1_GYM_ID)
    staff = await make_user(sessions, "staff", "onb-s1@example.com", DISTRICT_1_GYM_ID)
    pt = await make_user(sessions, "pt", "onb-pt@example.com", DISTRICT_1_GYM_ID)
    insights = "/api/v1/admin/analytics/onboarding-insights"

    assert (await client.get(insights, headers=auth_header(staff))).status_code == 403
    assert (await client.get(insights, headers=auth_header(pt))).status_code == 403
    assert (await client.get(insights, params={"gym_id": str(DISTRICT_11_GYM_ID)}, headers=auth_header(manager_1))).status_code == 403
    assert (await client.get(insights, params={"gym_id": str(DISTRICT_1_GYM_ID)}, headers=auth_header(manager_1))).status_code == 200
    assert (await client.get(insights, params={"gym_id": str(DISTRICT_11_GYM_ID)}, headers=auth_header(owner))).status_code == 200

    async with sessions() as session:
        for index in range(4):
            member = User(name=f"r{index}", email=f"onb-r{index}@example.com", role="member", password_hash="x")
            session.add(member)
            await session.flush()
            session.add(MemberOnboardingProfile(
                user_id=member.id, is_new_to_gym=True, prefers_uncrowded_hours=index % 2 == 0,
                closer_gym_id=DISTRICT_11_GYM_ID, completed_at=datetime.now(UTC),
            ))
        await session.commit()
    four = (await client.get(insights, params={"gym_id": str(DISTRICT_11_GYM_ID)}, headers=auth_header(owner))).json()
    assert four["respondents"] is None and four["respondents_suppressed"] is True
    assert all(metric["suppressed"] and not metric["buckets"] for metric in four["metrics"])

    async with sessions() as session:
        member = User(name="r5", email="onb-r5@example.com", role="member", password_hash="x")
        session.add(member)
        await session.flush()
        session.add(MemberOnboardingProfile(
            user_id=member.id, is_new_to_gym=True, prefers_uncrowded_hours=True,
            closer_gym_id=DISTRICT_11_GYM_ID, completed_at=datetime.now(UTC),
        ))
        await session.commit()
    five = (await client.get(insights, params={"gym_id": str(DISTRICT_11_GYM_ID)}, headers=auth_header(owner))).json()
    assert five["respondents"] == 5
    new_to_gym = next(item for item in five["metrics"] if item["key"] == "is_new_to_gym")
    assert new_to_gym["answered"] == 5 and new_to_gym["buckets"][0]["count"] == 5
    uncrowded = next(item for item in five["metrics"] if item["key"] == "prefers_uncrowded_hours")
    assert any(bucket["suppressed"] and bucket["count"] is None for bucket in uncrowded["buckets"])
