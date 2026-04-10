from fastapi import APIRouter, UploadFile, File
from services.cloudinary import upload_image

router = APIRouter()

@router.post("/")
def upload(file: UploadFile = File(...)):
    url = upload_image(file)
    return {"url": url}