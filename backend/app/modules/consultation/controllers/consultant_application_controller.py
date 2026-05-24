from fastapi import File
from sqlmodel import Session

from app.models import User,ConsultantApplication,ConsultantApplicationDocumentType
from app.modules.consultation.schemas import (
    ConsultantApplicationDocumentRead,
    ConsultantApplicationUpdate,
    ConsultantApplicationCreate,
    ConsultantApplicationRead,
    MessageResponse,
)
from app.modules.consultation.services.consultant_application_service import (
    add_application_document,
    create_application,
    get_application,
    remove_application_document,
    update_application,
)


def create_application_controller(
    session: Session,
    user: User,
    data: ConsultantApplicationCreate,
) -> ConsultantApplication:
    return create_application(session, user, data)


def get_application_controller(
    session: Session,
    user: User,
) -> ConsultantApplication:
    return get_application(session, user)


def update_application_controller(
    session: Session,
    user: User,
    data: ConsultantApplicationUpdate,
) -> ConsultantApplication:
    return update_application(session, user, data)


async def upload_application_document_controller(
    session: Session,
    user: User,
    file:File,
    document_type: ConsultantApplicationDocumentType,
) -> ConsultantApplicationDocumentRead:
    return await add_application_document(session, user, document_type, file)


def remove_application_document_controller(
    session: Session,
    user: User,
    document_id: str,
) -> MessageResponse:
    return remove_application_document(session, user, document_id)