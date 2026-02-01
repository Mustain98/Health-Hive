from __future__ import annotations

from datetime import time as time_type
from typing import Optional

from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.consultant import ConsultantProfile, ConsultantAvailabilityRule
from app.schemas.consultant import AvailabilityRuleCreate, AvailabilityRuleUpdate


def list_rules(session: Session, consultant_profile_id: int) -> list[ConsultantAvailabilityRule]:
    """Get all availability rules for a consultant profile."""
    return list(
        session.exec(
            select(ConsultantAvailabilityRule)
            .where(ConsultantAvailabilityRule.consultant_profile_id == consultant_profile_id)
        ).all()
    )


def create_rule(
    session: Session,
    consultant_profile_id: int,
    rule_data: AvailabilityRuleCreate,
) -> ConsultantAvailabilityRule:
    """Create a new availability rule."""
    # Parse time strings to time objects
    start = time_type.fromisoformat(rule_data.start_time)
    end = time_type.fromisoformat(rule_data.end_time)
    
    # Validate
    if start >= end:
        raise HTTPException(400, "Start time must be before end time")
    
    if not (0 <= rule_data.day_of_week <= 6):
        raise HTTPException(400, "Day of week must be 0-6 (Monday-Sunday)")
    
    rule = ConsultantAvailabilityRule(
        consultant_profile_id=consultant_profile_id,
        day_of_week=rule_data.day_of_week,
        start_time=start,
        end_time=end,
        timezone=rule_data.timezone,
        consultation_duration=rule_data.consultation_duration,
        is_active=True,
    )
    
    session.add(rule)
    session.commit()
    session.refresh(rule)
    
    return rule


def update_rule(
    session: Session,
    rule_id: int,
    consultant_profile_id: int,
    updates: AvailabilityRuleUpdate,
) -> ConsultantAvailabilityRule:
    """Update an existing availability rule."""
    rule = session.get(ConsultantAvailabilityRule, rule_id)
    if not rule:
        raise HTTPException(404, "Availability rule not found")
    
    if rule.consultant_profile_id != consultant_profile_id:
        raise HTTPException(403, "Not authorized to update this rule")
    
    # Update fields
    if updates.start_time is not None:
        rule.start_time = time_type.fromisoformat(updates.start_time)
    
    if updates.end_time is not None:
        rule.end_time = time_type.fromisoformat(updates.end_time)
    
    if updates.consultation_duration is not None:
        rule.consultation_duration = updates.consultation_duration
    
    if updates.is_active is not None:
        rule.is_active = updates.is_active
    
    # Validate times
    if rule.start_time >= rule.end_time:
        raise HTTPException(400, "Start time must be before end time")
    
    session.add(rule)
    session.commit()
    session.refresh(rule)
    
    return rule


def delete_rule(session: Session, rule_id: int, consultant_profile_id: int) -> None:
    """Delete an availability rule."""
    rule = session.get(ConsultantAvailabilityRule, rule_id)
    if not rule:
        raise HTTPException(404, "Availability rule not found")
    
    if rule.consultant_profile_id != consultant_profile_id:
        raise HTTPException(403, "Not authorized to delete this rule")
    
    session.delete(rule)
    session.commit()


def get_default_rules(consultant_profile_id: int) -> list[dict]:
    """Generate default Mon-Fri 9AM-5PM rules (for reference, not DB insert)."""
    defaults = []
    for day in range(5):  # Monday to Friday
        defaults.append({
            "day_of_week": day,
            "start_time": "09:00",
            "end_time": "17:00",
            "timezone": "Asia/Dhaka",
            "consultation_duration": 30,
        })
    return defaults
