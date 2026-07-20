from fastapi import APIRouter

from .food_item import router as food_item_router
from .meal import router as meal_router

router = APIRouter()
router.include_router(food_item_router)
router.include_router(meal_router)
