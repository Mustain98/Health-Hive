from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import create_db_and_tables

# Import models so SQLModel metadata includes all tables at startup
from app.models import (  # noqa: F401
    user,
    user_data,
    user_goal,
    nutrition_target,
    consultant,
    appointments,
    consultant_access,
)

from app.routers.auth import auth_router
from app.routers.user_data import user_data_router
from app.routers.goal_router import goal_router
from app.routers.nutrition_target_router import router as nutrition_target_router
from app.routers.consultant_router import router as consultant_router
from app.routers.appointment_router import router as appointment_router
from app.routers.session_router import router as session_router
from app.routers.permission_router import router as permission_router
from app.routers.consultant_manage_router import router as consultant_manage_router
from app.routers.video_router import router as video_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Health Hive API", lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base API prefix
app.include_router(auth_router, prefix="/api")
app.include_router(user_data_router, prefix="/api")
app.include_router(goal_router, prefix="/api")
app.include_router(nutrition_target_router, prefix="/api")

# New consultant/appointments/sessions/permissions
app.include_router(consultant_router, prefix="/api")
app.include_router(appointment_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(permission_router, prefix="/api")
app.include_router(consultant_manage_router, prefix="/api")


app.include_router(video_router, prefix="/api")