from fastapi import APIRouter

from .auth import auth_router
from .user_data import user_data_router
from .health_profile import router as health_profile_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(user_data_router)
router.include_router(health_profile_router)
