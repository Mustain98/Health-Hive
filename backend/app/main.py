from fastapi import FastAPI
from app.routers.auth import auth_router
from contextlib import asynccontextmanager 
from app.core.database import create_db_and_tables
from app.routers.auth import auth_router
from app.routers.user_data import user_data_router   
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager



async def lifespan(app:FastAPI):
    print("App is running")
    create_db_and_tables()
    print("db table created")
    yield
    print("app is shutting down")

app=FastAPI(lifespan=lifespan)


origins=[
    "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(user_data_router, prefix="/api")