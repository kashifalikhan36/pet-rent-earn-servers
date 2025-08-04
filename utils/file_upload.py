import os
import uuid
import magic
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io
from core.config import get_settings

settings = get_settings()


async def upload_image_file(file: UploadFile, subfolder: str = "general") -> str:
    """Upload and process image file"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Verify file type using python-magic
    try:
        mime_type = magic.from_buffer(content, mime=True)
        if not mime_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file"
            )
    except Exception:
        # Fallback if python-magic is not available
        pass
    
    # Get file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # Process image (resize if too large)
    try:
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Resize if image is too large
        max_size = (1920, 1920)  # Max dimensions
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save processed image
        processed_content = io.BytesIO()
        image.save(processed_content, format='JPEG', quality=85, optimize=True)
        content = processed_content.getvalue()
        file_extension = '.jpg'
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file or processing error"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_extension}"
    
    # Create directory structure
    upload_dir = os.path.join(settings.UPLOAD_DIRECTORY, subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, filename)
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )
    
    # Return file URL (relative to static files mount)
    return f"/uploads/{subfolder}/{filename}"


async def upload_document_file(file: UploadFile, subfolder: str = "documents") -> str:
    """Upload document file for verification"""
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Get file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_DOCUMENT_EXTENSIONS)}"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_extension}"
    
    # Create directory structure
    upload_dir = os.path.join(settings.UPLOAD_DIRECTORY, subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, filename)
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )
    
    # Return file URL
    return f"/uploads/{subfolder}/{filename}"


def delete_file(file_url: str) -> bool:
    """Delete uploaded file"""
    try:
        # Convert URL to file path
        if file_url.startswith("/uploads/"):
            file_path = os.path.join(settings.UPLOAD_DIRECTORY, file_url[9:])
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
    except Exception:
        pass
    return False


def get_file_info(file_url: str) -> Optional[dict]:
    """Get file information"""
    try:
        if file_url.startswith("/uploads/"):
            file_path = os.path.join(settings.UPLOAD_DIRECTORY, file_url[9:])
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "exists": True
                }
    except Exception:
        pass
    return {"exists": False} 