from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importing models registers every SQLModel table on SQLModel.metadata so
# create_db_and_tables() creates them all on startup.
from app import models  # noqa: F401
from app.core.database import create_db_and_tables
from app.core.logging_config import configure_logging
from app.routes import api_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Health Hive API", lifespan=lifespan)

# Local dev origins, plus any deployed frontends from CORS_ORIGINS (comma-separated).
# Credentials are allowed, so this can never be "*".
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
origins = DEV_ORIGINS + [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
