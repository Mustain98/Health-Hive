from fastapi import HTTPException, status, UploadFile

import cloudinary
from cloudinary import uploader

from .config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_NAME,
)


print("CLOUDINARY_NAME:", CLOUDINARY_NAME)
print("CLOUDINARY_API_KEY exists:", bool(CLOUDINARY_API_KEY))
print("CLOUDINARY_API_SECRET exists:", bool(CLOUDINARY_API_SECRET))


cloudinary.config(
    cloud_name=CLOUDINARY_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def get_resource_type(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"

    return "raw"


async def upload_file_to_cloudinary(
    file: UploadFile,
    collection_name: str,
) -> dict:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG, PNG, and WEBP files are allowed",
        )

    try:
        resource_type = get_resource_type(file.content_type)

        result = uploader.upload(
            file.file,
            folder=f"healthhive/{collection_name}",
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )

        return {
            "file_url": result["secure_url"],
            "public_id": result["public_id"],
            "resource_type": result["resource_type"],
            "file_name": file.filename,
            "content_type": file.content_type,
            "file_size": file.size,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cloudinary upload failed: {str(e)}",
        )


def delete_file_from_cloudinary(
    public_id: str,
    resource_type: str,
) -> None:
    try:
        result = uploader.destroy(
            public_id,
            resource_type=resource_type,
        )

        if result.get("result") not in ["ok", "not found"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cloudinary delete failed",
            )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cloudinary delete failed: {str(e)}",
        )