import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

def upload_image(file):
    if not all((cloudinary.config().cloud_name, cloudinary.config().api_key, cloudinary.config().api_secret)):
        raise RuntimeError("Cloudinary is not configured")
    res = cloudinary.uploader.upload(file.file)
    return res["secure_url"]