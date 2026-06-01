# image_utils.py
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

def validate_image(file_content: bytes, filename: str) -> tuple[bool, str]:
    """Validate image file type and size"""
    # Check size
    if len(file_content) > MAX_FILE_SIZE:
        return False, f"File too large. Maximum {MAX_FILE_SIZE // (1024*1024)}MB"
    
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Verify it's actually an image
    try:
        Image.open(BytesIO(file_content))
        return True, "Valid"
    except Exception:
        return False, "File is not a valid image"

def save_image(file_content: bytes, original_filename: str) -> str:
    """Save image to local storage and return the filename/path"""
    # Generate unique filename
    ext = Path(original_filename).suffix.lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / unique_filename
    
    # Save the file
    with open(filepath, "wb") as f:
        f.write(file_content)
    
    # Optional: Create thumbnail (200x200)
    try:
        img = Image.open(filepath)
        thumbnail_filename = f"thumb_{unique_filename}"
        thumbnail_path = UPLOAD_DIR / thumbnail_filename
        img.thumbnail((200, 200))
        img.save(thumbnail_path, optimize=True, quality=85)
    except Exception:
        pass  # Continue even if thumbnail fails
    
    return unique_filename  # Return just the filename

def delete_image(filename: str):
    """Delete image file and its thumbnail from storage"""
    if not filename:
        return
    
    try:
        # Delete original
        original_path = UPLOAD_DIR / filename
        if original_path.exists():
            original_path.unlink()
        
        # Delete thumbnail
        thumbnail_path = UPLOAD_DIR / f"thumb_{filename}"
        if thumbnail_path.exists():
            thumbnail_path.unlink()
    except Exception as e:
        print(f"Error deleting image: {e}")