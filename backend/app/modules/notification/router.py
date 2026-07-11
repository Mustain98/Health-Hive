import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.notification import service
from app.modules.notification.schemas import NotificationRead, UnreadCount

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return service.list_for_user(session, me.id)


@router.get("/unread-count", response_model=UnreadCount)
def get_unread_count(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return UnreadCount(unread=service.unread_count(session, me.id))


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return service.mark_read(session, me.id, notification_id)


@router.post("/read-all")
def read_all(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return {"marked": service.mark_all_read(session, me.id)}
