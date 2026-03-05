"""
Quick debug script – calls create_followup_from_session directly to see the real error.
Run: python debug_followup.py
"""
import os, uuid
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from app.core.database import engine

# Use a real appointment ID from your DB
APPOINTMENT_ID = uuid.UUID("0606a552-f2b7-4306-bb25-1a910c7d4340")

from app.models.followup import FollowUpRoom   # ensure table registered
from app.models.appointments import Appointment

with Session(engine) as session:
    appt = session.get(Appointment, APPOINTMENT_ID)
    if not appt:
        print("❌ Appointment not found")
        raise SystemExit(1)
    print(f"✅ Appointment found: user_id={appt.user_id}  consultant={appt.consultant_user_id}")
    print(f"   followup_room_id: {appt.followup_room_id}")
    
    CONSULTANT_ID = appt.consultant_user_id

    from app.service.followup_service import create_followup_from_session
    try:
        room = create_followup_from_session(session, APPOINTMENT_ID, CONSULTANT_ID)
        print(f"✅ Room created/found: {room.id}")
    except Exception as e:
        import traceback
        print("❌ Error:")
        traceback.print_exc()
