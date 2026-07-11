from fastapi import APIRouter

from .food_item_router import router as food_item_router
from .meal_router import router as meal_router
from .meal_plan_setting_router import router as meal_plan_setting_router

router = APIRouter()
router.include_router(food_item_router)
router.include_router(meal_router)
router.include_router(meal_plan_setting_router)
