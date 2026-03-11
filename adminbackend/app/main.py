import sys
import os
sys.path.append(os.path.dirname(__file__))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.admin_router import router as admin_router
from routers.auth_router import router as auth_router



app = FastAPI(title="Health Hive Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"status": "Admin API running"}