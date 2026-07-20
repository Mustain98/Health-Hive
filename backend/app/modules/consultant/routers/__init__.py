from fastapi import APIRouter

from .consultant import router as consultant_router
from .manage import router as consultant_manage_router

router = APIRouter()
router.include_router(consultant_router)
router.include_router(consultant_manage_router)
