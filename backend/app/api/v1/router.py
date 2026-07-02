from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, health, membership_plans, memberships, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(membership_plans.router)
api_router.include_router(memberships.router)
api_router.include_router(billing.router)
