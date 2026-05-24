from fastapi import HTTPException, status, File
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.models import (
    User,
    ConsultantApplication,
    ConsultantApplicationDocument,
    ConsultantApplicationDocumentType
)
from app.modules.consultation.models.consultant_application import utc_now
from app.modules.consultation.schemas import (
    ConsultantApplicationDocumentRead,
    ConsultantApplicationUpdate,
    MessageResponse,
)
from app.core.cloudinary import upload_file_to_cloudinary,delete_file_from_cloudinary


def build_document_read(
    doc: ConsultantApplicationDocument,
) -> ConsultantApplicationDocumentRead:
    return ConsultantApplicationDocumentRead(
        id=doc.id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        file_url=doc.file_url,
        file_name=doc.file_name,
        content_type=doc.content_type,
        file_size=doc.file_size,
        uploaded_at=doc.uploaded_at,
    )

def get_application(
    session: Session,
    user: User,
):
    application = session.exec(
        select(ConsultantApplication)
        .where(ConsultantApplication.user_id == user.id)
        .options(selectinload(ConsultantApplication.documents))
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultant application not found",
        )

    return application

def create_application(
    session: Session,
    user: User,
    data: ConsultantApplication,
) -> ConsultantApplication:
    existing_application = session.exec(
        select(ConsultantApplication).where(
            ConsultantApplication.user_id == user.id
        )
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied as a consultant",
        )

    application = ConsultantApplication(
        user_id=user.id,
        consultant_type=data.consultant_type,
        full_name=data.full_name,
        bio=data.bio,
        specialization=data.specialization,
        experience_years=data.experience_years,
        license_number=data.license_number,
        organization=data.organization,
    )

    session.add(application)
    session.commit()
    session.refresh(application)

    return application

def update_application(
    session: Session,
    user: User,
    data: ConsultantApplicationUpdate,
) ->ConsultantApplication :
    application = get_application(session, user)

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(application, key, value)

    application.updated_at = utc_now()

    session.add(application)
    session.commit()
    session.refresh(application)

    return application

async def add_application_document(
    session: Session,
    user: User,
    document_type: ConsultantApplicationDocumentType,
    file:File
) -> ConsultantApplicationDocumentRead:
    
    application = get_application(session, user)
    uploaded=await upload_file_to_cloudinary(file,"application_documents")
    document = ConsultantApplicationDocument(
        application_id=application.id,
        document_type=document_type,
        file_url=uploaded["file_url"],
        public_id=uploaded["public_id"],
        resource_type=uploaded["resource_type"],
        file_name=uploaded["file_name"],
        content_type=uploaded["content_type"],
        file_size=uploaded["file_size"],
    )

    session.add(document)
    session.commit()
    session.refresh(document)

    return build_document_read(document)

def remove_application_document(
    session: Session,
    user: User,
    document_id: str,
) -> MessageResponse:
    application = get_application(session, user)

    document = session.exec(
        select(ConsultantApplicationDocument).where(
            ConsultantApplicationDocument.id == document_id,
            ConsultantApplicationDocument.application_id == application.id,
        )
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    delete_file_from_cloudinary(
        public_id=document.public_id,
        resource_type=document.resource_type,
    )

    session.delete(document)
    session.commit()

    return MessageResponse(message=f"Document {document_id} deleted")