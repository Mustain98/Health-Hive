"""Root route aggregator.

Combines every feature module's router under the shared ``/api`` prefix.
"""
from fastapi import APIRouter

from app.modules.user.router import router as user_router
from app.modules.consultant.router import router as consultant_router
from app.modules.appointment.router import router as appointment_router
from app.modules.meal.router import router as meal_router
from app.modules.meal_planner_agent.router import router as meal_planner_agent_router

api_router = APIRouter(prefix="/api")
api_router.include_router(user_router)
api_router.include_router(consultant_router)
api_router.include_router(appointment_router)
api_router.include_router(meal_router)
api_router.include_router(meal_planner_agent_router)
