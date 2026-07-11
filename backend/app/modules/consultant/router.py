from fastapi import APIRouter

from .consultant_router import router as consultant_router
from .consultant_manage_router import router as consultant_manage_router

router = APIRouter()
router.include_router(consultant_router)
router.include_router(consultant_manage_router)
