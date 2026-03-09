import asyncio
from sqlmodel import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
db_string = os.getenv("DATABASE_URL")
if not db_string:
    print("No DATABASE_URL found.")
else:
    engine = create_engine(db_string)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE meal ADD COLUMN IF NOT EXISTS image_url VARCHAR;"))
        conn.commit()
    print("Database updated.")
