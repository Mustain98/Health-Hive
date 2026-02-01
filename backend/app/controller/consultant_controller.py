from __future__ import annotations

from fastapi import UploadFile
from sqlmodel import Session

from app.models.user import User
from app.models.consultant import ConsultantProfile, ConsultantDocument
from app.schemas.consultant import ConsultantProfileCreate, ConsultantProfileUpdate, ConsultantDocumentCreate
from app.service.consultant_service import (
    upsert_my_profile,
    update_my_profile,
    search_consultants,
    get_profile_public,
    get_profile_by_user_id,
    add_document_supabase,
    list_documents,
)


def upsert_profile_me(session: Session, me: User, payload: ConsultantProfileCreate) -> ConsultantProfile:
    return upsert_my_profile(
        session,
        me,
        display_name=payload.display_name,
        bio=payload.bio,
        specialties=payload.specialties,
        other_info=payload.other_info,
        consultant_type=payload.consultant_type,
        highest_qualification=payload.highest_qualification,
        graduation_institution=payload.graduation_institution,
        registration_body=payload.registration_body,
        registration_number=payload.registration_number,
    )


def update_profile_me(session: Session, me: User, payload: ConsultantProfileUpdate) -> ConsultantProfile:
    return update_my_profile(
        session,
        me,
        display_name=payload.display_name,
        bio=payload.bio,
        specialties=payload.specialties,
        other_info=payload.other_info,
        consultant_type=payload.consultant_type,
        highest_qualification=payload.highest_qualification,
        graduation_institution=payload.graduation_institution,
        registration_body=payload.registration_body,
        registration_number=payload.registration_number,
    )


def search_public(session: Session, query: str | None, verified_only: bool, limit: int, offset: int) -> list[ConsultantProfile]:
    return search_consultants(session, query=query, verified_only=verified_only, limit=limit, offset=offset)


def read_public_profile(session: Session, profile_id: int) -> ConsultantProfile:
    return get_profile_public(session, profile_id)


def read_my_profile(session: Session, me: User) -> ConsultantProfile | None:
    return get_profile_by_user_id(session, me.id)


def upload_document_me(
    session: Session,
    me: User,
    profile_id: int,
    meta: ConsultantDocumentCreate,
    file: UploadFile,
) -> ConsultantDocument:
    return add_document_supabase(
        session,
        me,
        profile_id,
        doc_type=meta.doc_type,
        issuer=meta.issuer,
        issue_date=meta.issue_date,
        expires_at=meta.expires_at,
        file=file,
    )


def list_profile_documents(session: Session, profile_id: int) -> list[ConsultantDocument]:
    return list_documents(session, profile_id)


# ============= Availability Rules =============

def list_my_availability_rules(session: Session, consultant: User):
    """List all availability rules for the consultant."""
    from app.service.availability_service import list_rules
    from fastapi import HTTPException
    
    profile = get_profile_by_user_id(session, consultant.id)
    if not profile:
        raise HTTPException(404, "Consultant profile not found")
    
    rules = list_rules(session, profile.id)
    
    # Convert time objects to strings
    from app.schemas.consultant import AvailabilityRuleRead
    return [
        AvailabilityRuleRead(
            id=r.id,
            consultant_profile_id=r.consultant_profile_id,
            day_of_week=r.day_of_week,
            start_time=r.start_time.strftime("%H:%M"),
            end_time=r.end_time.strftime("%H:%M"),
            timezone=r.timezone,
            consultation_duration=r.consultation_duration,
            is_active=r.is_active,
        )
        for r in rules
    ]


def create_availability_rule(session: Session, consultant: User, rule_data):
    """Create a new availability rule."""
    from app.service.availability_service import create_rule
    from fastapi import HTTPException
    
    profile = get_profile_by_user_id(session, consultant.id)
    if not profile:
        raise HTTPException(404, "Consultant profile not found")
    
    rule = create_rule(session, profile.id, rule_data)
    
    from app.schemas.consultant import AvailabilityRuleRead
    return AvailabilityRuleRead(
        id=rule.id,
        consultant_profile_id=rule.consultant_profile_id,
        day_of_week=rule.day_of_week,
        start_time=rule.start_time.strftime("%H:%M"),
        end_time=rule.end_time.strftime("%H:%M"),
        timezone=rule.timezone,
        consultation_duration=rule.consultation_duration,
        is_active=rule.is_active,
    )


def update_availability_rule(session: Session, consultant: User, rule_id: int, updates):
    """Update an availability rule."""
    from app.service.availability_service import update_rule
    from fastapi import HTTPException
    
    profile = get_profile_by_user_id(session, consultant.id)
    if not profile:
        raise HTTPException(404, "Consultant profile not found")
    
    rule = update_rule(session, rule_id, profile.id, updates)
    
    from app.schemas.consultant import AvailabilityRuleRead
    return AvailabilityRuleRead(
        id=rule.id,
        consultant_profile_id=rule.consultant_profile_id,
        day_of_week=rule.day_of_week,
        start_time=rule.start_time.strftime("%H:%M"),
        end_time=rule.end_time.strftime("%H:%M"),
        timezone=rule.timezone,
        consultation_duration=rule.consultation_duration,
        is_active=rule.is_active,
    )


def delete_availability_rule(session: Session, consultant: User, rule_id: int):
    """Delete an availability rule."""
    from app.service.availability_service import delete_rule
    from fastapi import HTTPException
    
    profile = get_profile_by_user_id(session, consultant.id)
    if not profile:
        raise HTTPException(404, "Consultant profile not found")
    
    delete_rule(session, rule_id, profile.id)
