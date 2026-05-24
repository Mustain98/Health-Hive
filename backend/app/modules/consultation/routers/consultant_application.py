from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models import User,ConsultantApplication,ConsultantApplicationDocumentType
from app.modules.consultation.schemas import (
    ConsultantApplicationCreate,
    ConsultantApplicationDocumentRead,
    ConsultantApplicationUpdate,
    MessageResponse,
)
from app.modules.consultation.controllers.consultant_application_controller import (
    upload_application_document_controller,
    create_application_controller,
    get_application_controller,
    remove_application_document_controller,
    update_application_controller,
)

router = APIRouter(prefix="/consultant", tags=["consultant"])


@router.get("/apply", response_model=ConsultantApplication)
def get_my_application(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return get_application_controller(session, user)


@router.post("/apply", response_model=ConsultantApplication)
def apply_as_consultant(
    data: ConsultantApplicationCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return create_application_controller(session, user, data)


@router.patch("/apply", response_model=ConsultantApplication)
def update_my_application(
    data: ConsultantApplicationUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return update_application_controller(session, user, data)


@router.post("/apply/documents", response_model=ConsultantApplicationDocumentRead)
async def upload_application_document(
    document_type: ConsultantApplicationDocumentType = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await upload_application_document_controller(
        session=session,
        user=user,
        document_type=document_type,
        file=file,
    )


@router.delete("/apply/document/{document_id}", response_model=MessageResponse)
def delete_application_document(
    document_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return remove_application_document_controller(session, user, document_id)