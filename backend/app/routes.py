"""Root route aggregator.

Combines every feature module's router under the shared ``/api`` prefix.
Each module exposes its aggregate router as ``<module>.routers.router``, and every
router carries its own prefix — so moving a router between modules never changes a URL.
"""
from fastapi import APIRouter

from app.modules.user.routers import router as user_router
from app.modules.milestone.routers import router as milestone_router
from app.modules.daily_goal.routers import router as daily_goal_router
from app.modules.nutrition_target.routers import router as nutrition_target_router
from app.modules.meal_plan_setting.routers import router as meal_plan_setting_router
from app.modules.plan.routers import router as plan_router
from app.modules.consultant.routers import router as consultant_router
from app.modules.appointment.routers import router as appointment_router
from app.modules.consultation.routers import router as consultation_router
from app.modules.meal.routers import router as meal_router
from app.agents.router import router as agents_router
from app.modules.notification.routers import router as notification_router

api_router = APIRouter(prefix="/api")

# Plan parts
api_router.include_router(milestone_router)
api_router.include_router(daily_goal_router)
api_router.include_router(nutrition_target_router)
api_router.include_router(meal_plan_setting_router)
api_router.include_router(plan_router)

# Everything else
api_router.include_router(user_router)
api_router.include_router(consultant_router)
api_router.include_router(appointment_router)
api_router.include_router(consultation_router)
api_router.include_router(meal_router)
api_router.include_router(agents_router)
api_router.include_router(notification_router)
