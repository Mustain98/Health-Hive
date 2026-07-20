"""Aggregates the appointment routers. Include order preserved from the old router.py."""
from fastapi import APIRouter

from .appointment import router as appointment_router
from .session import router as session_router
from .followup import router as followup_router
from .video import router as video_router

router = APIRouter()
router.include_router(appointment_router)
router.include_router(session_router)
router.include_router(followup_router)
router.include_router(video_router)
