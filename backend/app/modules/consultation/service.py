from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.consultation.models import (
    ConsultationRequest,
    ConsultationChat,
    ConsultationMessage,
    ConsultationProposal,
    RequestStatus,
    ChatStatus,
    ProposalStatus,
    ConsultationRequestRead,
    ConsultationChatRead,
)
from app.modules.user.models import User, UserType
from app.utils.time import utc_now


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_request(session: Session, request_id: uuid.UUID) -> ConsultationRequest:
    req = session.get(ConsultationRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


def _get_chat(session: Session, chat_id: uuid.UUID) -> ConsultationChat:
    chat = session.get(ConsultationChat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def _require_chat_participant(chat: ConsultationChat, user_id: uuid.UUID):
    if user_id not in (chat.user_id, chat.consultant_user_id):
        raise HTTPException(status_code=403, detail="You are not a participant in this chat")


def _party_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    return user.full_name or user.username


def _enrich_request(session: Session, req: ConsultationRequest, me_id: uuid.UUID) -> ConsultationRequestRead:
    other_id = req.consultant_user_id if req.user_id == me_id else req.user_id
    other = session.get(User, other_id)
    return ConsultationRequestRead(
        **req.model_dump(),
        other_party_name=_party_name(other),
        other_party_email=other.email if other else None,
    )


def _enrich_chat(session: Session, chat: ConsultationChat, me_id: uuid.UUID) -> ConsultationChatRead:
    other_id = chat.consultant_user_id if chat.user_id == me_id else chat.user_id
    other = session.get(User, other_id)
    return ConsultationChatRead(
        **chat.model_dump(),
        other_party_name=_party_name(other),
        other_party_email=other.email if other else None,
    )


def _insert_message(session: Session, chat_id: uuid.UUID, sender_id: uuid.UUID, text: str, is_system: bool = False) -> ConsultationMessage:
    msg = ConsultationMessage(
        chat_id=chat_id,
        sender_user_id=sender_id,
        message=text,
        is_system=is_system,
        sent_at=utc_now(),
    )
    session.add(msg)
    return msg


# ─── Requests ────────────────────────────────────────────────────────────────

def create_request(
    session: Session,
    user_id: uuid.UUID,
    consultant_user_id: uuid.UUID,
    issue: str,
) -> ConsultationRequest:
    consultant = session.get(User, consultant_user_id)
    if not consultant or consultant.user_type != UserType.consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if consultant_user_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot request a consultation with yourself")
    if not issue or not issue.strip():
        raise HTTPException(status_code=400, detail="Please describe your issue")

    # Block duplicate: an existing pending request for this pair
    pending = session.exec(
        select(ConsultationRequest)
        .where(ConsultationRequest.user_id == user_id)
        .where(ConsultationRequest.consultant_user_id == consultant_user_id)
        .where(ConsultationRequest.status == RequestStatus.pending)
    ).first()
    if pending:
        raise HTTPException(status_code=409, detail="You already have a pending request with this consultant")

    # Block duplicate: an open chat already exists for this pair
    open_chat = session.exec(
        select(ConsultationChat)
        .where(ConsultationChat.user_id == user_id)
        .where(ConsultationChat.consultant_user_id == consultant_user_id)
        .where(ConsultationChat.status == ChatStatus.open)
    ).first()
    if open_chat:
        raise HTTPException(status_code=409, detail="You already have an open chat with this consultant")

    now = utc_now()
    req = ConsultationRequest(
        user_id=user_id,
        consultant_user_id=consultant_user_id,
        issue=issue.strip(),
        status=RequestStatus.pending,
        created_at=now,
        updated_at=now,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


def list_my_requests(session: Session, user_id: uuid.UUID) -> list[ConsultationRequestRead]:
    reqs = session.exec(
        select(ConsultationRequest)
        .where(ConsultationRequest.user_id == user_id)
        .order_by(ConsultationRequest.created_at.desc())
    ).all()
    return [_enrich_request(session, r, user_id) for r in reqs]


def list_incoming_requests(
    session: Session,
    consultant_id: uuid.UUID,
    status: Optional[RequestStatus] = None,
) -> list[ConsultationRequestRead]:
    stmt = (
        select(ConsultationRequest)
        .where(ConsultationRequest.consultant_user_id == consultant_id)
    )
    if status is not None:
        stmt = stmt.where(ConsultationRequest.status == status)
    stmt = stmt.order_by(ConsultationRequest.created_at.desc())
    reqs = session.exec(stmt).all()
    return [_enrich_request(session, r, consultant_id) for r in reqs]


def reply_to_request(
    session: Session,
    request_id: uuid.UUID,
    consultant_id: uuid.UUID,
    message: str,
) -> ConsultationChat:
    """Consultant replies → creates the chat, seeds it with the issue + reply."""
    req = _get_request(session, request_id)
    if req.consultant_user_id != consultant_id:
        raise HTTPException(status_code=403, detail="This request was not addressed to you")
    if req.status == RequestStatus.declined:
        raise HTTPException(status_code=409, detail="Request was declined")
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Reply cannot be empty")

    now = utc_now()

    # Reuse existing open chat for this request if it somehow exists
    if req.chat_id:
        existing = session.get(ConsultationChat, req.chat_id)
        if existing:
            _insert_message(session, existing.id, consultant_id, message.strip())
            existing.last_message_at = now
            existing.updated_at = now
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

    chat = ConsultationChat(
        request_id=req.id,
        user_id=req.user_id,
        consultant_user_id=consultant_id,
        status=ChatStatus.open,
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(chat)
    session.flush()  # get chat.id

    # Seed: the user's original issue, then the consultant's reply
    _insert_message(session, chat.id, req.user_id, req.issue)
    _insert_message(session, chat.id, consultant_id, message.strip())

    req.status = RequestStatus.accepted
    req.chat_id = chat.id
    req.responded_at = now
    req.updated_at = now
    session.add(req)

    session.commit()
    session.refresh(chat)
    return chat


def decline_request(
    session: Session,
    request_id: uuid.UUID,
    consultant_id: uuid.UUID,
) -> ConsultationRequest:
    req = _get_request(session, request_id)
    if req.consultant_user_id != consultant_id:
        raise HTTPException(status_code=403, detail="This request was not addressed to you")
    if req.status != RequestStatus.pending:
        raise HTTPException(status_code=409, detail=f"Request is already {req.status.value}")

    now = utc_now()
    req.status = RequestStatus.declined
    req.responded_at = now
    req.updated_at = now
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


# ─── Chats ───────────────────────────────────────────────────────────────────

def list_my_chats(session: Session, me_id: uuid.UUID) -> list[ConsultationChatRead]:
    chats = session.exec(
        select(ConsultationChat)
        .where(
            (ConsultationChat.user_id == me_id) |
            (ConsultationChat.consultant_user_id == me_id)
        )
        .order_by(ConsultationChat.last_message_at.desc(), ConsultationChat.created_at.desc())
    ).all()
    return [_enrich_chat(session, c, me_id) for c in chats]


def get_chat_detail(session: Session, chat_id: uuid.UUID, me_id: uuid.UUID) -> ConsultationChatRead:
    chat = _get_chat(session, chat_id)
    _require_chat_participant(chat, me_id)
    return _enrich_chat(session, chat, me_id)


def list_messages(
    session: Session,
    chat_id: uuid.UUID,
    me_id: uuid.UUID,
    skip: int = 0,
    limit: int = 200,
) -> list[ConsultationMessage]:
    chat = _get_chat(session, chat_id)
    _require_chat_participant(chat, me_id)
    return list(
        session.exec(
            select(ConsultationMessage)
            .where(ConsultationMessage.chat_id == chat_id)
            .order_by(ConsultationMessage.sent_at.asc())
            .offset(skip)
            .limit(limit)
        ).all()
    )


def post_message(
    session: Session,
    chat_id: uuid.UUID,
    sender_id: uuid.UUID,
    text: str,
    is_system: bool = False,
) -> ConsultationMessage:
    chat = _get_chat(session, chat_id)
    if not is_system:
        _require_chat_participant(chat, sender_id)
    if chat.status == ChatStatus.closed:
        raise HTTPException(status_code=409, detail="Chat is closed")
    if not is_system and (not text or not text.strip()):
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = _insert_message(session, chat_id, sender_id, text.strip() if not is_system else text, is_system)
    chat.last_message_at = msg.sent_at
    chat.updated_at = utc_now()
    session.add(chat)
    session.commit()
    session.refresh(msg)
    return msg


# ─── Proposals ───────────────────────────────────────────────────────────────

def create_proposal(
    session: Session,
    chat_id: uuid.UUID,
    proposer_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
) -> ConsultationProposal:
    chat = _get_chat(session, chat_id)
    _require_chat_participant(chat, proposer_id)

    # Only the consultant proposes times; the user accepts/rejects.
    if proposer_id != chat.consultant_user_id:
        raise HTTPException(status_code=403, detail="Only the consultant can propose a time")
    if chat.status == ChatStatus.closed:
        raise HTTPException(status_code=409, detail="Cannot propose in a closed chat")
    if start_at >= end_at:
        raise HTTPException(status_code=400, detail="start_at must be before end_at")
    if start_at < utc_now():
        raise HTTPException(status_code=400, detail="Cannot propose a time in the past")

    now = utc_now()
    proposal = ConsultationProposal(
        chat_id=chat_id,
        proposed_by_user_id=proposer_id,
        start_at=start_at,
        end_at=end_at,
        status=ProposalStatus.pending,
        created_at=now,
        updated_at=now,
    )
    session.add(proposal)
    session.flush()

    start_fmt = start_at.strftime("%d %b %Y, %H:%M")
    end_fmt = end_at.strftime("%H:%M")
    proposer = session.get(User, proposer_id)
    label = _party_name(proposer) or "Someone"
    _insert_message(session, chat_id, proposer_id,
                    f"📅 {label} proposed a time: {start_fmt}–{end_fmt}", is_system=True)
    chat.last_message_at = now
    chat.updated_at = now
    session.add(chat)

    session.commit()
    session.refresh(proposal)
    return proposal


def list_proposals(session: Session, chat_id: uuid.UUID, me_id: uuid.UUID) -> list[ConsultationProposal]:
    chat = _get_chat(session, chat_id)
    _require_chat_participant(chat, me_id)
    return list(
        session.exec(
            select(ConsultationProposal)
            .where(ConsultationProposal.chat_id == chat_id)
            .order_by(ConsultationProposal.created_at.desc())
        ).all()
    )


def accept_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    acceptor_id: uuid.UUID,
) -> ConsultationProposal:
    """Accepting a proposal books the fixed consultation: Appointment + SessionRoom."""
    from app.modules.appointment.models import Appointment, SessionRoom, AppointmentStatus, SessionStatus

    proposal = session.get(ConsultationProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    chat = _get_chat(session, proposal.chat_id)
    _require_chat_participant(chat, acceptor_id)

    if proposal.proposed_by_user_id == acceptor_id:
        raise HTTPException(status_code=400, detail="Cannot accept your own proposal")
    if proposal.status != ProposalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Proposal is already {proposal.status.value}")

    now = utc_now()

    appt = Appointment(
        user_id=chat.user_id,
        consultant_user_id=chat.consultant_user_id,
        scheduled_start_at=proposal.start_at,
        scheduled_end_at=proposal.end_at,
        status=AppointmentStatus.scheduled,
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
    label = _party_name(acceptor) or "User"
    _insert_message(session, proposal.chat_id, acceptor_id,
                    f"✅ {label} accepted the proposal. Consultation scheduled for {start_fmt}.", is_system=True)
    chat.last_message_at = now
    chat.updated_at = now
    session.add(chat)

    session.commit()
    session.refresh(proposal)
    return proposal


def reject_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    rejector_id: uuid.UUID,
) -> ConsultationProposal:
    proposal = session.get(ConsultationProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    chat = _get_chat(session, proposal.chat_id)
    _require_chat_participant(chat, rejector_id)

    if proposal.proposed_by_user_id == rejector_id:
        raise HTTPException(status_code=400, detail="Cannot reject your own proposal")
    if proposal.status != ProposalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Proposal is already {proposal.status.value}")

    now = utc_now()
    proposal.status = ProposalStatus.rejected
    proposal.responded_by_user_id = rejector_id
    proposal.responded_at = now
    proposal.updated_at = now
    session.add(proposal)

    rejector = session.get(User, rejector_id)
    label = _party_name(rejector) or "User"
    _insert_message(session, proposal.chat_id, rejector_id,
                    f"❌ {label} rejected the proposed time.", is_system=True)
    chat.last_message_at = now
    chat.updated_at = now
    session.add(chat)

    session.commit()
    session.refresh(proposal)
    return proposal


def cancel_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    requester_id: uuid.UUID,
) -> ConsultationProposal:
    proposal = session.get(ConsultationProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    chat = _get_chat(session, proposal.chat_id)
    _require_chat_participant(chat, requester_id)

    if proposal.proposed_by_user_id != requester_id:
        raise HTTPException(status_code=403, detail="Only the proposer can cancel")
    if proposal.status != ProposalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Proposal is already {proposal.status.value}")

    now = utc_now()
    proposal.status = ProposalStatus.cancelled
    proposal.updated_at = now
    session.add(proposal)

    canceller = session.get(User, requester_id)
    label = _party_name(canceller) or "User"
    _insert_message(session, proposal.chat_id, requester_id,
                    f"🚫 {label} cancelled the proposed time.", is_system=True)
    chat.last_message_at = now
    chat.updated_at = now
    session.add(chat)

    session.commit()
    session.refresh(proposal)
    return proposal
