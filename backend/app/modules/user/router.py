from fastapi import APIRouter

from .auth_router import auth_router
from .user_data_router import user_data_router
from .goal_router import goal_router
from .nutrition_target_router import router as nutrition_target_router
from .health_profile_router import router as health_profile_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(user_data_router)
router.include_router(goal_router)
router.include_router(nutrition_target_router)
router.include_router(health_profile_router)
