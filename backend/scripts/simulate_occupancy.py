"""Fill a gym with synthetic attendance so the occupancy UI can be seen at Low, Moderate, Busy and Very Crowded.

Run inside the backend container from /app:

    python -m scripts.simulate_occupancy --list
    python -m scripts.simulate_occupancy --gym district-1 --level low
    python -m scripts.simulate_occupancy --gym district-1 --level medium
    python -m scripts.simulate_occupancy --gym district-1 --level high
    python -m scripts.simulate_occupancy --gym district-11 --percent 70
    python -m scripts.simulate_occupancy --gym district-1 --count 40
    python -m scripts.simulate_occupancy --clear            # remove all simulated data

How it works
- It creates throw-away members named "Occupancy Sim NNN" (email occsim-<gym>-NNNN@ypgym.sim, no password,
  so nobody can sign in as them) and gives each one an ACTIVE attendance session at the chosen gym.
- Occupancy is "active sessions / gym capacity", the same number the app computes. Real members who are
  genuinely checked in are counted too, so the script only adds the difference up to the target.
- Running it again for the same gym replaces its earlier simulated sessions, so you can switch levels freely.
- It clears the 30-second Redis occupancy cache and publishes a realtime event, so pages that are already
  open update on their own.
- Check-in times are spread over the last 50 minutes. The timeout worker closes active sessions after
  attendance_timeout_minutes (180 by default, checked every 5 minutes). Re-run the script to refresh them.
- It never touches real users or real sessions, and it refuses to run when ENVIRONMENT is production.
"""
import argparse
import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.redis import get_redis_client
from app.db.session import AsyncSessionLocal, engine
from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.gym import GymLocation
from app.models.user import User
from app.schemas.attendance_schema import AttendanceRealtimeEvent
from app.services.attendance_realtime_service import AttendanceRealtimePublisher
from app.services.attendance_service import CrowdednessService, crowdedness_status

SIM_SOURCE = "occupancy_sim"
SIM_DOMAIN = "ypgym.sim"
SIM_PREFIX = "occsim-"

# Percent of capacity for each named level. Each sits inside the band the app uses:
# <=30 Low, <=60 Moderate, <=85 Busy, above that Very Crowded.
LEVELS = {
    "low": 20,
    "moderate": 50,
    "busy": 75,
    "crowded": 95,
}
ALIASES = {"medium": "moderate", "high": "crowded", "very-crowded": "crowded", "full": "crowded"}


def sim_email_pattern(slug: str | None = None) -> str:
    return f"{SIM_PREFIX}{slug}-%@{SIM_DOMAIN}" if slug else f"{SIM_PREFIX}%@{SIM_DOMAIN}"


async def find_gym(session, key: str) -> GymLocation:
    gyms = (await session.execute(select(GymLocation).order_by(GymLocation.name))).scalars().all()
    wanted = key.strip().lower()
    for gym in gyms:
        if wanted in {gym.slug.lower(), str(gym.id).lower(), gym.name.lower(), gym.district.lower()}:
            return gym
    names = ", ".join(gym.slug for gym in gyms) or "none"
    raise SystemExit(f"Unknown gym '{key}'. Available: {names}")


async def active_counts(session, gym: GymLocation) -> tuple[int, int]:
    """(real active sessions, simulated active sessions) for one gym."""
    total = int(
        (await session.execute(
            select(func.count(AttendanceSession.id)).where(
                AttendanceSession.gym_id == gym.id, AttendanceSession.status == "active",
            ),
        )).scalar_one(),
    )
    simulated = int(
        (await session.execute(
            select(func.count(AttendanceSession.id)).where(
                AttendanceSession.gym_id == gym.id,
                AttendanceSession.status == "active",
                AttendanceSession.source == SIM_SOURCE,
            ),
        )).scalar_one(),
    )
    return total - simulated, simulated


async def remove_simulated(session, slug: str | None = None) -> int:
    """Delete simulated users; their sessions and events go with them (ON DELETE CASCADE)."""
    result = await session.execute(delete(User).where(User.email.like(sim_email_pattern(slug))))
    return result.rowcount or 0


async def create_simulated(session, gym: GymLocation, count: int) -> None:
    now = datetime.now(UTC)
    rng = random.Random()
    for index in range(1, count + 1):
        user = User(
            id=uuid4(),
            name=f"Occupancy Sim {index:03d}",
            email=f"{SIM_PREFIX}{gym.slug}-{index:04d}@{SIM_DOMAIN}",
            role="member",
            is_email_verified=True,
            password_hash=None,
        )
        session.add(user)
        await session.flush()
        checked_in_at = now - timedelta(minutes=rng.randint(1, 50), seconds=rng.randint(0, 59))
        attendance = AttendanceSession(
            id=uuid4(),
            gym_id=gym.id,
            user_id=user.id,
            checked_in_at=checked_in_at,
            status="active",
            source=SIM_SOURCE,
        )
        session.add(attendance)
        await session.flush()
        session.add(
            AttendanceEvent(
                id=uuid4(),
                gym_id=gym.id,
                session_id=attendance.id,
                user_id=user.id,
                event_type="check_in",
                event_at=checked_in_at,
                source=SIM_SOURCE,
            ),
        )


async def refresh_and_announce(session, redis, gym: GymLocation, action: str):
    """Drop the cached occupancy, recompute it and tell open pages to reload."""
    await redis.delete(CrowdednessService.cache_key(gym.id))
    occupancy = await CrowdednessService(session, redis).get(gym_id=gym.id, force_reconcile=True)
    event = AttendanceRealtimeEvent(
        event_id=uuid4(),
        gym_id=gym.id,
        kind="occupancy_changed",
        action=action,
        occurred_at=datetime.now(UTC),
        occupancy_calculated_at=occupancy.calculated_at,
        request_id=f"occupancy-sim-{uuid4().hex[:12]}",
    )
    await AttendanceRealtimePublisher(redis).publish([event])
    return occupancy


def describe(gym: GymLocation, active: int, real: int | None = None) -> str:
    percent = round(active / gym.capacity * 100, 1) if gym.capacity else 0.0
    extra = f" (real: {real})" if real else ""
    return f"{gym.name}: {active}/{gym.capacity} = {percent}% -> {crowdedness_status(percent)}{extra}"


def target_from_args(args, capacity: int) -> int:
    if args.count is not None:
        return args.count
    percent = args.percent if args.percent is not None else LEVELS[args.level]
    return max(0, int(capacity * percent / 100 + 0.5))


async def run(args) -> None:
    if get_settings().ENVIRONMENT == "production":
        raise SystemExit("Refusing to run: ENVIRONMENT is production.")
    redis = await get_redis_client()
    try:
        async with AsyncSessionLocal() as session:
            gyms = (await session.execute(select(GymLocation).order_by(GymLocation.name))).scalars().all()

            if args.list:
                for gym in gyms:
                    real, simulated = await active_counts(session, gym)
                    print(describe(gym, real + simulated, real) + f" [simulated: {simulated}] slug={gym.slug}")
                return

            if args.clear:
                removed = await remove_simulated(session)
                await session.commit()
                print(f"Removed {removed} simulated members and their attendance.")
                for gym in gyms:
                    occupancy = await refresh_and_announce(session, redis, gym, "manual_close")
                    print(describe(gym, occupancy.active_count))
                return

            gym = await find_gym(session, args.gym)
            await remove_simulated(session, gym.slug)
            await session.flush()
            real, _ = await active_counts(session, gym)
            target = target_from_args(args, gym.capacity)
            if target > gym.capacity * 3:
                raise SystemExit(f"Target {target} is more than 3x the capacity ({gym.capacity}); check the numbers.")
            need = max(0, target - real)
            if real > target:
                print(f"Note: {real} real members are already checked in, above the target of {target}.")
            await create_simulated(session, gym, need)
            await session.commit()
            occupancy = await refresh_and_announce(session, redis, gym, "check_in")
            print(f"Added {need} simulated check-ins at {gym.name}.")
            print(describe(gym, occupancy.active_count, real))
            print("Open the member dashboard or the staff attendance page; it updates on its own within seconds.")
            print("Remove everything with: python -m scripts.simulate_occupancy --clear")
    finally:
        await engine.dispose()
        await redis.aclose()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Simulate gym occupancy for UI testing.")
    parser.add_argument("--gym", default="district-1", help="slug, id, name or district (default: district-1)")
    choices = sorted(set(LEVELS) | set(ALIASES))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--level", choices=choices, help="low, medium (moderate), busy or high (crowded)")
    mode.add_argument("--percent", type=float, help="target occupancy as a percent of capacity")
    mode.add_argument("--count", type=int, help="target number of people inside")
    mode.add_argument("--clear", action="store_true", help="remove all simulated members and sessions")
    mode.add_argument("--list", action="store_true", help="show current occupancy for every gym")
    args = parser.parse_args(argv)
    if args.level:
        args.level = ALIASES.get(args.level, args.level)
    if args.percent is not None and not 0 <= args.percent <= 300:
        parser.error("--percent must be between 0 and 300")
    if args.count is not None and args.count < 0:
        parser.error("--count must be 0 or more")
    return args


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
