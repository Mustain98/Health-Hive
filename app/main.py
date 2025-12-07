from fastapi import FastAPI
from app.routers.auth import auth_router
from contextlib import asynccontextmanager 
from app.core.database import create_db_and_tables
from app.routers.auth import auth_router

@asynccontextmanager

async def lifespan(app:FastAPI):
    print("App is running")
    create_db_and_tables()
    print("db table created")
    yield
    print("app is shutting down")

app=FastAPI(lifespan=lifespan)
app.include_router(auth_router, prefix="/api")
