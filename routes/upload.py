from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from auth.dependencies import get_current_admin_user
from services.cloudinary import upload_image
from routes.image_utils import validate_image

router = APIRouter()


@router.post("/")
def upload(file: UploadFile = File(...), user=Depends(get_current_admin_user)):
    """Upload an image to Cloudinary (admin only)"""
    contents = file.file.read()

    is_valid, error_msg = validate_image(contents, file.filename)
    if not is_valid:
        raise HTTPException(400, error_msg)

    file.file.seek(0)

    url = upload_image(file)
    return {"url": url}