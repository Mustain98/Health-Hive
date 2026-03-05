from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.followup import (
    FollowUpRoom,
    FollowUpMessage,
    TimeProposal,
    FollowUpRoomStatus,
    ProposalStatus,
    FollowUpRoomRead,
)
from app.models.user import User
from app.utils.time import utc_now


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_room(session: Session, room_id: uuid.UUID) -> FollowUpRoom:
    room = session.get(FollowUpRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Follow-up room not found")
    return room


def _require_participant(room: FollowUpRoom, user_id: uuid.UUID):
    if user_id not in (room.user_id, room.consultant_user_id):
        raise HTTPException(status_code=403, detail="You are not a participant in this room")


def _enrich_room(session: Session, room: FollowUpRoom, me_id: uuid.UUID) -> FollowUpRoomRead:
    other_id = room.consultant_user_id if room.user_id == me_id else room.user_id
    other = session.get(User, other_id)
    cancelled_by_name: Optional[str] = None
    if room.cancelled_by_user_id:
        canceller = session.get(User, room.cancelled_by_user_id)
        cancelled_by_name = canceller.full_name or canceller.username if canceller else None
    return FollowUpRoomRead(
        **room.model_dump(),
        other_party_name=other.full_name or other.username if other else None,
        other_party_email=other.email if other else None,
        cancelled_by_name=cancelled_by_name,
    )


# ─── Room lifecycle ────────────────────────────────────────────────────────────

def create_followup_from_session(
    session: Session,
    appointment_id: uuid.UUID,
    consultant_id: uuid.UUID,
) -> FollowUpRoom:
    """
    Create a follow-up room from an active session.
    - Only the consultant of that appointment can call this.
    - If a follow-up room already exists for this (user, consultant) pair, return it.
    - Stamps followup_room_id on the originating appointment so it appears first
      in the sessions list.

    FK ordering note: followup_rooms.created_from_appointment_id → appointments.id
    and appointments.followup_room_id → followup_rooms.id create a circular FK.
    We break the cycle with a two-step commit:
      1. Insert room WITHOUT created_from_appointment_id (satisfies appointments FK not yet set)
      2. Update both fields in a second commit
    """
    from app.models.appointments import Appointment

    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.consultant_user_id != consultant_id:
        raise HTTPException(status_code=403, detail="Only the assigned consultant can start a follow-up")

    # 1. Return existing ACTIVE room for this pair — no new room needed
    existing_active = session.exec(
        select(FollowUpRoom)
        .where(FollowUpRoom.user_id == appt.user_id)
        .where(FollowUpRoom.consultant_user_id == consultant_id)
        .where(FollowUpRoom.status == FollowUpRoomStatus.active)
    ).first()
    if existing_active:
        # Ensure the new appointment is linked to the active room
        if appt.followup_room_id != existing_active.id:
            appt.followup_room_id = existing_active.id
            appt.updated_at = utc_now()
            session.add(appt)
            session.commit()
        return existing_active

    now = utc_now()

    # 2. Reactivate the most recently closed room if one exists for this pair
    closed_room = session.exec(
        select(FollowUpRoom)
        .where(FollowUpRoom.user_id == appt.user_id)
        .where(FollowUpRoom.consultant_user_id == consultant_id)
        .where(FollowUpRoom.status == FollowUpRoomStatus.closed)
        .order_by(FollowUpRoom.cancelled_at.desc())
    ).first()

    if closed_room:
        closed_room.status = FollowUpRoomStatus.active
        closed_room.reactivated_at = now
        closed_room.cancelled_by_user_id = None
        closed_room.cancelled_at = None
        closed_room.updated_at = now
        session.add(closed_room)

        appt.followup_room_id = closed_room.id
        appt.updated_at = now
        session.add(appt)

        session.commit()
        session.refresh(closed_room)
        return closed_room

    # Step 1: insert room WITHOUT created_from_appointment_id to avoid circular FK
    room = FollowUpRoom(
        user_id=appt.user_id,
        consultant_user_id=consultant_id,
        status=FollowUpRoomStatus.active,
        created_from_appointment_id=None,   # set in step 2
        created_at=now,
        updated_at=now,
    )
    session.add(room)
    session.commit()
    session.refresh(room)

    # Step 2: update appointment → followup_room_id and room → created_from_appointment_id
    appt.followup_room_id = room.id
    appt.updated_at = now
    session.add(appt)

    room.created_from_appointment_id = appointment_id
    room.updated_at = now
    session.add(room)

    session.commit()
    session.refresh(room)
    return room


def cancel_followup(
    session: Session,
    room_id: uuid.UUID,
    requester_id: uuid.UUID,
) -> FollowUpRoom:
    """Either the user or the consultant can cancel the follow-up."""
    room = _get_room(session, room_id)
    _require_participant(room, requester_id)

    if room.status == FollowUpRoomStatus.closed:
        raise HTTPException(status_code=409, detail="Follow-up is already cancelled")

    now = utc_now()
    room.status = FollowUpRoomStatus.closed
    room.cancelled_by_user_id = requester_id
    room.cancelled_at = now
    room.updated_at = now
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def list_rooms_for_user(
    session: Session,
    me_id: uuid.UUID,
) -> list[FollowUpRoomRead]:
    rooms = session.exec(
        select(FollowUpRoom)
        .where(
            (FollowUpRoom.user_id == me_id) |
            (FollowUpRoom.consultant_user_id == me_id)
        )
        .order_by(FollowUpRoom.last_message_at.desc(), FollowUpRoom.created_at.desc())
    ).all()
    return [_enrich_room(session, r, me_id) for r in rooms]


def get_room_detail(
    session: Session,
    room_id: uuid.UUID,
    me_id: uuid.UUID,
) -> FollowUpRoomRead:
    room = _get_room(session, room_id)
    _require_participant(room, me_id)
    return _enrich_room(session, room, me_id)


# ─── Sessions list ─────────────────────────────────────────────────────────────

def list_sessions_for_room(
    session: Session,
    room_id: uuid.UUID,
    me_id: uuid.UUID,
) -> list:
    """
    Return all Appointments where followup_room_id == room_id, ordered by date.
    The originating appointment (where follow-up was created) is always first.
    """
    from app.models.appointments import Appointment
    room = _get_room(session, room_id)
    _require_participant(room, me_id)

    appointments = session.exec(
        select(Appointment)
        .where(Appointment.followup_room_id == room_id)
        .order_by(Appointment.scheduled_start_at.asc())
    ).all()
    return list(appointments)


# ─── Patient summary (consultant-only) ─────────────────────────────────────────

def get_patient_summary(
    session: Session,
    room_id: uuid.UUID,
    consultant_id: uuid.UUID,
) -> dict:
    """Return patient UserData, UserGoal (active or most recent), and NutritionTarget (active or most recent)."""
    from app.models.user_data import UserData, UserGoalLog
    from app.models.user_goal import UserGoal
    from app.models.nutrition_target import NutritionTarget

    room = _get_room(session, room_id)
    if room.consultant_user_id != consultant_id:
        raise HTTPException(status_code=403, detail="Only the assigned consultant can view patient summary")

    patient = session.get(User, room.user_id)
    user_data = session.exec(select(UserData).where(UserData.user_id == room.user_id)).first()

    # Prefer active goal; fall back to most recently created goal
    goal = session.exec(
        select(UserGoal)
        .where(UserGoal.created_for == room.user_id)
        .where(UserGoal.active == True)  # noqa: E712
    ).first()
    if not goal:
        goal = session.exec(
            select(UserGoal)
            .where(UserGoal.created_for == room.user_id)
            .order_by(UserGoal.created_at.desc())
        ).first()

    # Prefer active target; fall back to most recently created target
    target = session.exec(
        select(NutritionTarget)
        .where(NutritionTarget.created_for == room.user_id)
        .where(NutritionTarget.active == True)  # noqa: E712
    ).first()
    if not target:
        target = session.exec(
            select(NutritionTarget)
            .where(NutritionTarget.created_for == room.user_id)
            .order_by(NutritionTarget.created_at.desc())
        ).first()

    logs = []
    if goal:
        logs = session.exec(
            select(UserGoalLog)
            .where(UserGoalLog.goal_id == goal.id)
            .order_by(UserGoalLog.date.asc())
        ).all()

    return {
        "patient": patient,
        "user_data": user_data,
        "goal": goal,
        "nutrition_target": target,
        "logs": logs,
    }


def get_my_summary(
    session: Session,
    room_id: uuid.UUID,
    me_id: uuid.UUID,
) -> dict:
    """Return the user's own health data, goal (active or most recent), NutritionTarget, and Goal Logs."""
    from app.models.user_data import UserData, UserGoalLog
    from app.models.user_goal import UserGoal
    from app.models.nutrition_target import NutritionTarget

    room = _get_room(session, room_id)
    if room.user_id != me_id:
        raise HTTPException(status_code=403, detail="Not your follow-up room")

    patient = session.get(User, room.user_id)
    user_data = session.exec(select(UserData).where(UserData.user_id == room.user_id)).first()

    # Prefer active goal; fall back to most recently created goal
    goal = session.exec(
        select(UserGoal)
        .where(UserGoal.created_for == room.user_id)
        .where(UserGoal.active == True)
    ).first()
    if not goal:
        goal = session.exec(
            select(UserGoal)
            .where(UserGoal.created_for == room.user_id)
            .order_by(UserGoal.created_at.desc())
        ).first()

    # Prefer active target; fall back to most recently created target
    target = session.exec(
        select(NutritionTarget)
        .where(NutritionTarget.created_for == room.user_id)
        .where(NutritionTarget.active == True)
    ).first()
    if not target:
        target = session.exec(
            select(NutritionTarget)
            .where(NutritionTarget.created_for == room.user_id)
            .order_by(NutritionTarget.created_at.desc())
        ).first()

    logs = []
    if goal:
        logs = session.exec(
            select(UserGoalLog)
            .where(UserGoalLog.goal_id == goal.id)
            .order_by(UserGoalLog.date.asc())
        ).all()

    return {
        "patient": patient,
        "user_data": user_data,
        "goal": goal,
        "nutrition_target": target,
        "logs": logs,
    }

# ─── Messages ──────────────────────────────────────────────────────────────────

def post_message(
    session: Session,
    room_id: uuid.UUID,
    sender_id: uuid.UUID,
    text: str,
    is_system: bool = False,
) -> FollowUpMessage:
    room = _get_room(session, room_id)
    if not is_system:
        _require_participant(room, sender_id)
    if room.status == FollowUpRoomStatus.closed:
        raise HTTPException(status_code=409, detail="Room is cancelled")

    msg = FollowUpMessage(
        room_id=room_id,
        sender_user_id=sender_id,
        message=text,
        is_system=is_system,
        sent_at=utc_now(),
    )
    session.add(msg)

    room.last_message_at = msg.sent_at
    room.updated_at = utc_now()
    session.add(room)

    session.commit()
    session.refresh(msg)
    return msg


def list_messages(
    session: Session,
    room_id: uuid.UUID,
    me_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[FollowUpMessage]:
    room = _get_room(session, room_id)
    _require_participant(room, me_id)
    return list(
        session.exec(
            select(FollowUpMessage)
            .where(FollowUpMessage.room_id == room_id)
            .order_by(FollowUpMessage.sent_at.asc())
            .offset(skip)
            .limit(limit)
        ).all()
    )


# ─── Proposals ─────────────────────────────────────────────────────────────────

def create_proposal(
    session: Session,
    room_id: uuid.UUID,
    proposer_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
) -> TimeProposal:
    room = _get_room(session, room_id)
    _require_participant(room, proposer_id)

    if room.status == FollowUpRoomStatus.closed:
        raise HTTPException(status_code=409, detail="Cannot propose in a cancelled follow-up")
    if start_at >= end_at:
        raise HTTPException(status_code=400, detail="start_at must be before end_at")
    if start_at < utc_now():
        raise HTTPException(status_code=400, detail="Cannot propose a time in the past")

    proposal = TimeProposal(
        room_id=room_id,
        proposed_by_user_id=proposer_id,
        start_at=start_at,
        end_at=end_at,
        status=ProposalStatus.pending,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(proposal)
    session.flush()

    start_fmt = start_at.strftime("%d %b %Y, %H:%M")
    end_fmt = end_at.strftime("%H:%M")
    proposer = session.get(User, proposer_id)
    proposer_label = proposer.full_name or proposer.username if proposer else "Someone"
    _insert_system_msg(session, room_id, proposer_id,
                       f"📅 {proposer_label} proposed a time: {start_fmt}–{end_fmt}")

    session.commit()
    session.refresh(proposal)
    return proposal


def list_proposals(
    session: Session,
    room_id: uuid.UUID,
    me_id: uuid.UUID,
) -> list[TimeProposal]:
    room = _get_room(session, room_id)
    _require_participant(room, me_id)
    return list(
        session.exec(
            select(TimeProposal)
            .where(TimeProposal.room_id == room_id)
            .order_by(TimeProposal.created_at.desc())
        ).all()
    )


def accept_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    acceptor_id: uuid.UUID,
) -> TimeProposal:
    from app.models.appointments import Appointment, SessionRoom, AppointmentStatus, SessionStatus

    proposal = session.get(TimeProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    room = _get_room(session, proposal.room_id)
    _require_participant(room, acceptor_id)

    if proposal.proposed_by_user_id == acceptor_id:
        raise HTTPException(status_code=400, detail="Cannot accept your own proposal")
    if proposal.status != ProposalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Proposal is already {proposal.status}")

    now = utc_now()

    # Create appointment — stamp followup_room_id so it appears in follow-up sessions list
    appt = Appointment(
        user_id=room.user_id,
        consultant_user_id=room.consultant_user_id,
        scheduled_start_at=proposal.start_at,
        scheduled_end_at=proposal.end_at,
        status=AppointmentStatus.scheduled,
        followup_room_id=room.id,   # ← links this appointment to the follow-up room
        created_at=now,
        updated_at=now,
    )
    session.add(appt)
    session.flush()

    session_room = SessionRoom(
        appointment_id=appt.id,
        status=SessionStatus.not_started,
        created_at=now,
        updated_at=now,
    )
    session.add(session_room)

    proposal.status = ProposalStatus.accepted
    proposal.appointment_id = appt.id
    proposal.responded_by_user_id = acceptor_id
    proposal.responded_at = now
    proposal.updated_at = now
    session.add(proposal)

    start_fmt = proposal.start_at.strftime("%d %b %Y, %H:%M")
    acceptor = session.get(User, acceptor_id)
    acceptor_label = acceptor.full_name or acceptor.username if acceptor else "User"
    _insert_system_msg(session, proposal.room_id, acceptor_id,
                       f"✅ {acceptor_label} accepted the proposal. Appointment scheduled for {start_fmt}.")

    session.commit()
    session.refresh(proposal)
    return proposal


def reject_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    rejector_id: uuid.UUID,
) -> TimeProposal:
    proposal = session.get(TimeProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    room = _get_room(session, proposal.room_id)
    _require_participant(room, rejector_id)

    if proposal.proposed_by_user_id == rejector_id:
        raise HTTPException(status_code=400, detail="Cannot reject your own proposal")
    if proposal.status != ProposalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Proposal is already {proposal.status}")

    now = utc_now()
    proposal.status = ProposalStatus.rejected
    proposal.responded_by_user_id = rejector_id
    proposal.responded_at = now
    proposal.updated_at = now
    session.add(proposal)

    rejector = session.get(User, rejector_id)
    label = rejector.full_name or rejector.username if rejector else "User"
    _insert_system_msg(session, proposal.room_id, rejector_id,
                       f"❌ {label} rejected the proposed time.")

    session.commit()
    session.refresh(proposal)
    return proposal


def cancel_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    requester_id: uuid.UUID,
) -> TimeProposal:
    proposal = session.get(TimeProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    room = _get_room(session, proposal.room_id)
    _require_participant(room, requester_id)

    if proposal.proposed_by_user_id != requester_id:
        raise HTTPException(status_code=403, detail="Only the proposer can cancel")
    if proposal.status != ProposalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Proposal is already {proposal.status}")

    now = utc_now()
    proposal.status = ProposalStatus.cancelled
    proposal.updated_at = now
    session.add(proposal)

    canceller = session.get(User, requester_id)
    label = canceller.full_name or canceller.username if canceller else "User"
    _insert_system_msg(session, proposal.room_id, requester_id,
                       f"🚫 {label} cancelled the proposed time.")

    session.commit()
    session.refresh(proposal)
    return proposal


# ─── Internal ──────────────────────────────────────────────────────────────────

def _insert_system_msg(session: Session, room_id: uuid.UUID, sender_id: uuid.UUID, text: str):
    msg = FollowUpMessage(
        room_id=room_id,
        sender_user_id=sender_id,
        message=text,
        is_system=True,
        sent_at=utc_now(),
    )
    session.add(msg)
