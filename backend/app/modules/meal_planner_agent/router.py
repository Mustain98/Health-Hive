from fastapi import APIRouter

from .meal_plan_router import router as meal_plan_router
from .setup_chat_router import router as setup_chat_router

router = APIRouter()
router.include_router(meal_plan_router)
router.include_router(setup_chat_router)
