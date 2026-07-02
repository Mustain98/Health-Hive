from fastapi import APIRouter

from .meal_plan_router import router as meal_plan_router

router = APIRouter()
router.include_router(meal_plan_router)
