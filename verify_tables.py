from app.main import lifespan, app
from sqlmodel import create_engine, inspect
from app.core.database import DATABASE_URL
import os
import asyncio

# Ensure we use the same DB
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)

async def test_startup():
    print("Testing startup lifespan...")
    async with lifespan(app):
        print("Startup complete. Checking tables...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print("Existing Tables:", tables)
        if "users" in tables:
            print("SUCCESS: 'users' table found.")
        else:
            print("FAILURE: 'users' table NOT found.")
            exit(1)

if __name__ == "__main__":
    asyncio.run(test_startup())
