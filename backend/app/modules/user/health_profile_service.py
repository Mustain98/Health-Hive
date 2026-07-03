from __future__ import annotations

import uuid
from typing import Optional

from sqlmodel import Session

from app.modules.user.models import UserHealthProfile
from app.utils.time import utc_now


def get_health_profile(session: Session, user_id: uuid.UUID) -> Optional[UserHealthProfile]:
    return session.get(UserHealthProfile, user_id)


def upsert_health_profile(
    session: Session,
    user_id: uuid.UUID,
    diet_preferences: list,
    health_conditions: list,
    notes: Optional[str],
) -> UserHealthProfile:
    now = utc_now()
    profile = session.get(UserHealthProfile, user_id)
    # Store enum values as plain strings in the JSON columns
    diet = [d.value if hasattr(d, "value") else d for d in diet_preferences]
    conditions = [c.value if hasattr(c, "value") else c for c in health_conditions]

    if profile:
        profile.diet_preferences = diet
        profile.health_conditions = conditions
        profile.notes = notes
        profile.updated_at = now
    else:
        profile = UserHealthProfile(
            user_id=user_id,
            diet_preferences=diet,
            health_conditions=conditions,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
