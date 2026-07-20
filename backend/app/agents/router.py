"""Aggregates the agent-facing routers under /api (prefixes unchanged)."""
from fastapi import APIRouter

from app.agents.meal_plan.router import router as meal_plan_router
from app.agents.setup_chat.router import router as setup_chat_router

router = APIRouter()
router.include_router(meal_plan_router)
router.include_router(setup_chat_router)
