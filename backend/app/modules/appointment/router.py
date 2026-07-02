from fastapi import APIRouter

from .appointment_router import router as appointment_router
from .session_router import router as session_router
from .followup_router import router as followup_router
from .video_router import router as video_router

router = APIRouter()
router.include_router(appointment_router)
router.include_router(session_router)
router.include_router(followup_router)
router.include_router(video_router)
