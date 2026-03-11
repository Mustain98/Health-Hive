import sqlite3
import os

from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv("DATABASE_URL")
db_path = db_url.replace("sqlite:///", "") if db_url else "database.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()
try:
    cur.execute("SELECT count(*) FROM consultant_applications;")
    print("Table exists:", cur.fetchone()[0])
except Exception as e:
    print("Error:", e)
