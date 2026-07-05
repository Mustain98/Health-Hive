"""Notification service — small, reusable across modules.

`create` is called by other services (setup chatbot, daily log, risk referral).
It does NOT commit by default so callers can include it in their own transaction;
pass commit=True for a standalone notification.
"""
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.modules.notification.models import Notification, NotificationType


def create(
    session: Session,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    body: Optional[str] = None,
    data: Optional[dict] = None,
    commit: bool = False,
) -> Notification:
    n = Notification(user_id=user_id, type=type, title=title, body=body, data=data or {})
    session.add(n)
    if commit:
        session.commit()
        session.refresh(n)
    else:
        session.flush()
    return n


def list_for_user(session: Session, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
    return list(session.exec(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    ).all())


def unread_count(session: Session, user_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read == False)  # noqa: E712
    ).one()


def mark_read(session: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    n = session.get(Notification, notification_id)
    if not n or n.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    session.add(n)
    session.commit()
    session.refresh(n)
    return n


def mark_all_read(session: Session, user_id: uuid.UUID) -> int:
    rows = session.exec(
        select(Notification).where(Notification.user_id == user_id, Notification.read == False)  # noqa: E712
    ).all()
    for n in rows:
        n.read = True
        session.add(n)
    session.commit()
    return len(rows)
