from fastapi import APIRouter

from app.api.v1.endpoints import admin, attendance, auth, billing, classes, dashboard, health, membership_plans, memberships, notifications, training, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(membership_plans.router)
api_router.include_router(memberships.router)
api_router.include_router(billing.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(attendance.router)
api_router.include_router(attendance.analytics_router)
api_router.include_router(classes.router)
api_router.include_router(classes.trainer_router)
api_router.include_router(classes.admin_trainer_router)
api_router.include_router(classes.member_class_router)
api_router.include_router(classes.booking_router)
api_router.include_router(dashboard.router)
api_router.include_router(training.router)
api_router.include_router(training.admin_router)
api_router.include_router(training.workout_router)
