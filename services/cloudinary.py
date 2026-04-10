import cloudinary.uploader

def upload_image(file):
    res = cloudinary.uploader.upload(file.file)
    return res["secure_url"]