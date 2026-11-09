from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.gym import GymLocation
from app.models.onboarding import MemberOnboardingProfile
from app.models.user import User
from app.repositories.gym_repository import GymRepository
from app.repositories.membership_repository import UserMembershipRepository
from app.repositories.onboarding_repository import OnboardingRepository
from app.schemas.onboarding_schema import (
    GymSplitRow,
    InsightBucket,
    InsightMetric,
    OnboardingAnswers,
    OnboardingInsightsResponse,
    OnboardingResponse,
    QuietHours,
    RecommendationsResponse,
    RecommendedGym,
)
from app.services.gym_service import GymScopeService
from app.services.traffic_analytics_service import TrafficAnalyticsService

# Hours covered by each training window, as [start, end) in the gym's local time.
TRAINING_WINDOW_HOURS = {
    "early_morning": (5, 8),
    "daytime": (8, 16),
    "evening": (16, 20),
    "night": (20, 24),
}

ANSWER_FIELDS = (
    "is_new_to_gym",
    "prefers_uncrowded_hours",
    "closer_gym_id",
    "main_goal",
    "training_window",
    "days_per_week",
    "interested_in_classes",
    "interested_in_personal_trainer",
)

_METRICS: list[tuple[str, str, str, list[tuple[object, str]]]] = [
    ("is_new_to_gym", "is_new_to_gym", "New to the gym", [(True, "Yes"), (False, "No")]),
    ("prefers_uncrowded_hours", "prefers_uncrowded_hours", "Prefers uncrowded hours", [(True, "Yes"), (False, "No")]),
    (
        "main_goal",
        "main_goal",
        "Main goal",
        [
            ("lose_weight", "Lose weight"),
            ("build_muscle", "Build muscle"),
            ("stay_fit", "Stay fit and healthy"),
            ("stamina", "Improve stamina"),
            ("not_sure", "Not sure yet"),
        ],
    ),
    (
        "training_window",
        "training_window",
        "Usual training time",
        [
            ("early_morning", "Early morning"),
            ("daytime", "Daytime"),
            ("evening", "Evening"),
            ("night", "Night"),
        ],
    ),
    ("days_per_week", "days_per_week", "Days per week", [("1_2", "1 to 2"), ("3_4", "3 to 4"), ("5_plus", "5 or more")]),
    ("interested_in_classes", "interested_in_classes", "Interested in group classes", [(True, "Yes"), (False, "No")]),
    (
        "interested_in_personal_trainer",
        "interested_in_personal_trainer",
        "Interested in a personal trainer",
        [(True, "Yes"), (False, "No")],
    ),
]


def profile_status(profile: MemberOnboardingProfile | None) -> str:
    if profile is None:
        return "not_started"
    if (
        profile.is_new_to_gym is not None
        and profile.prefers_uncrowded_hours is not None
        and profile.closer_gym_id is not None
    ):
        return "complete"
    if any(getattr(profile, field) is not None for field in ANSWER_FIELDS):
        return "partial"
    return "skipped" if profile.dismissed_at else "not_started"


def pick_quiet_window(buckets, training_window: str | None):
    """Quietest two-hour bucket, restricted to the member's training window when one was answered."""
    candidates = list(buckets)
    if training_window in TRAINING_WINDOW_HOURS:
        start, end = TRAINING_WINDOW_HOURS[training_window]
        candidates = [item for item in candidates if item.start_hour < end and item.end_hour > start]
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item.average_headcount, item.start_hour))


class OnboardingService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None) -> None:
        self.session = session
        self.redis = redis
        self.profiles = OnboardingRepository(session)
        self.gyms = GymRepository(session)

    @staticmethod
    def _response(profile: MemberOnboardingProfile | None) -> OnboardingResponse:
        if profile is None:
            return OnboardingResponse(status="not_started")
        return OnboardingResponse(
            status=profile_status(profile),
            completed_at=profile.completed_at,
            dismissed_at=profile.dismissed_at,
            **{field: getattr(profile, field) for field in ANSWER_FIELDS},
        )

    async def get(self, *, user: User) -> OnboardingResponse:
        return self._response(await self.profiles.get(user.id))

    async def save(self, *, user: User, payload: OnboardingAnswers) -> OnboardingResponse:
        if payload.closer_gym_id is not None:
            gym = await self.gyms.get_location(payload.closer_gym_id, active_only=True)
            if not gym:
                raise AppError("ONBOARDING_GYM_INVALID", "Choose one of the available gym locations.", 422)
        profile = await self.profiles.get(user.id)
        if profile is None:
            profile = MemberOnboardingProfile(user_id=user.id)
            self.profiles.add(profile)
        for field in ANSWER_FIELDS:
            setattr(profile, field, getattr(payload, field))
        complete = profile_status(profile) == "complete"
        profile.completed_at = (profile.completed_at or datetime.now(UTC)) if complete else None
        await self.session.commit()
        await self.session.refresh(profile)
        return self._response(profile)

    async def skip(self, *, user: User) -> OnboardingResponse:
        profile = await self.profiles.get(user.id)
        if profile is None:
            profile = MemberOnboardingProfile(user_id=user.id)
            self.profiles.add(profile)
        profile.dismissed_at = profile.dismissed_at or datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(profile)
        return self._response(profile)

    async def recommendations(self, *, user: User) -> RecommendationsResponse:
        profile = await self.profiles.get(user.id)
        if profile is None:
            return RecommendationsResponse()
        result = RecommendationsResponse()
        recommended: GymLocation | None = None
        if profile.closer_gym_id is not None:
            recommended = await self.gyms.get_location(profile.closer_gym_id, active_only=True)
            if recommended:
                result.recommended_gym = RecommendedGym(
                    id=recommended.id,
                    name=recommended.name,
                    slug=recommended.slug,
                    district=recommended.district,
                )
        if profile.prefers_uncrowded_hours is True and self.redis is not None:
            quiet_gym = recommended
            if quiet_gym is None:
                membership = await UserMembershipRepository(self.session).get_latest_for_user(user.id)
                if membership:
                    quiet_gym = await self.gyms.get_location(membership.home_gym_id, active_only=True)
            if quiet_gym is not None:
                summary = await TrafficAnalyticsService(self.session, self.redis).get(gym_id=quiet_gym.id)
                window = pick_quiet_window(summary.buckets, profile.training_window) if summary.data_sufficient else None
                if window is None:
                    result.quiet_hours_reason = "not_enough_data"
                else:
                    result.quiet_hours = QuietHours(
                        gym_id=quiet_gym.id,
                        gym_name=quiet_gym.name,
                        label=window.label,
                        start_hour=window.start_hour,
                        end_hour=window.end_hour,
                        average_capacity_percentage=window.average_capacity_percentage,
                    )
        return result

    async def insights(self, *, user: User, gym_id: UUID | None) -> OnboardingInsightsResponse:
        scope = GymScopeService(self.session)
        if user.role == "admin":
            if gym_id is not None:
                await scope.require_access(user=user, requested_gym_id=gym_id)
            effective = gym_id
        else:
            effective = await scope.resolve_gym_id(user=user, requested_gym_id=gym_id)
        minimum = get_settings().ONBOARDING_INSIGHT_MIN_GROUP_SIZE
        members = (
            (await self.profiles.home_gym_counts()).get(effective, 0)
            if effective is not None
            else await self.profiles.count_members()
        )
        respondents = await self.profiles.count_respondents(gym_id=effective)
        metrics: list[InsightMetric] = []
        for key, column, label, options in _METRICS:
            counts = await self.profiles.answer_counts(column, gym_id=effective)
            answered = sum(counts.values())
            if answered < minimum:
                metrics.append(InsightMetric(key=key, label=label, suppressed=True))
                continue
            buckets = []
            for value, option_label in options:
                count = counts.get(value, 0)
                if count < minimum:
                    buckets.append(InsightBucket(key=str(value).lower(), label=option_label, suppressed=True))
                else:
                    buckets.append(
                        InsightBucket(
                            key=str(value).lower(),
                            label=option_label,
                            count=count,
                            percent=round(count / answered * 100, 1),
                        ),
                    )
            metrics.append(InsightMetric(key=key, label=label, answered=answered, buckets=buckets))
        split: list[GymSplitRow] = []
        if effective is None:
            closer = await self.profiles.closer_gym_counts()
            home = await self.profiles.home_gym_counts()
            for gym in await self.gyms.list_locations(active_only=True):
                closer_count, home_count = closer.get(gym.id, 0), home.get(gym.id, 0)
                split.append(
                    GymSplitRow(
                        gym_id=gym.id,
                        gym_name=gym.name,
                        closer_count=closer_count if closer_count >= minimum else None,
                        closer_suppressed=closer_count < minimum,
                        home_members=home_count if home_count >= minimum else None,
                        home_suppressed=home_count < minimum,
                    ),
                )
        suppressed = respondents < minimum
        return OnboardingInsightsResponse(
            gym_id=effective,
            min_group_size=minimum,
            members=members,
            respondents=None if suppressed else respondents,
            respondents_suppressed=suppressed,
            response_rate_percent=(
                round(respondents / members * 100, 1) if effective is None and members and not suppressed else None
            ),
            metrics=metrics,
            gym_split=split,
            generated_at=datetime.now(UTC),
        )
