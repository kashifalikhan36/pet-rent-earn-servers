from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, File, UploadFile
from typing import List, Dict, Any, Optional
from datetime import date

from schemas.health_record import (
    HealthRecordCreate, HealthRecordUpdate, HealthRecordOut, RecordType
)
from dependencies.auth import get_current_active_user
from crud.health_record import (
    create_health_record, update_health_record, delete_health_record,
    get_health_record, get_pet_health_records, check_health_record_access,
    get_recent_or_upcoming_health_records, upload_health_record_attachment
)
from utils.file_upload import upload_document_file
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/by-pet/{pet_id}", response_model=HealthRecordOut)
async def create_health_record_endpoint(
    pet_id: str,
    record: HealthRecordCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create a health record for a pet"""
    owner_id = current_user["id"]
    
    result = await create_health_record(
        pet_id=pet_id,
        owner_id=owner_id,
        record_data=record.dict(),
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission"
        )
    
    return result


@router.put("/{record_id}", response_model=HealthRecordOut)
async def update_health_record_endpoint(
    record_id: str,
    record: HealthRecordUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update a health record"""
    owner_id = current_user["id"]
    
    result = await update_health_record(
        record_id=record_id,
        owner_id=owner_id,
        record_data=record.dict(exclude_unset=True),
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found or you don't have permission"
        )
    
    return result


@router.delete("/{record_id}")
async def delete_health_record_endpoint(
    record_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete a health record"""
    owner_id = current_user["id"]
    
    success = await delete_health_record(
        record_id=record_id,
        owner_id=owner_id,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found or you don't have permission"
        )
    
    return {"message": "Health record deleted successfully"}


@router.get("/{record_id}", response_model=HealthRecordOut)
async def get_health_record_endpoint(
    record_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get a health record by ID"""
    # Check if user has access to health record
    has_access = await check_health_record_access(
        record_id=record_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this health record"
        )
    
    record = await get_health_record(
        record_id=record_id,
        request=request
    )
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found"
        )
    
    return record


@router.get("/by-pet/{pet_id}", response_model=List[HealthRecordOut])
async def get_pet_health_records_endpoint(
    pet_id: str,
    record_type: Optional[RecordType] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    request: Request = None,
    current_user = Depends(get_current_active_user)
):
    """Get health records for a pet"""
    # Get pet from database to check ownership
    database = request.app.mongodb
    from bson import ObjectId
    
    pet = await database.pets.find_one({"_id": ObjectId(pet_id)})
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    # Check if user is owner or has active booking
    is_owner = pet.get("owner_id") == current_user["id"]
    
    if not is_owner:
        # Check if renter has active booking and owner allows access
        has_booking = await database.bookings.find_one({
            "pet_id": pet_id,
            "renter_id": current_user["id"],
            "status": "confirmed",
            "end_date": {"$gte": date.today()}
        })
        
        allows_access = pet.get("share_health_records_with_renters", False)
        
        if not has_booking or not allows_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view health records for this pet"
            )
    
    skip = (page - 1) * per_page
    
    records = await get_pet_health_records(
        pet_id=pet_id,
        record_type=record_type,
        skip=skip,
        limit=per_page,
        request=request
    )
    
    return records


@router.get("/recent-activity", response_model=List[Dict[str, Any]])
async def get_recent_health_activity(
    request: Request,
    limit: int = Query(5, ge=1, le=20),
    current_user = Depends(get_current_active_user)
):
    """Get recent health records and upcoming reminders for user's pets"""
    owner_id = current_user["id"]
    
    records = await get_recent_or_upcoming_health_records(
        owner_id=owner_id,
        request=request,
        limit=limit
    )
    
    return records


@router.post("/{record_id}/attachments", response_model=Dict[str, Any])
async def upload_attachment(
    record_id: str,
    request: Request,
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user)
):
    """Upload attachment for health record"""
    owner_id = current_user["id"]
    
    # Check file type
    allowed_types = [
        "application/pdf", 
        "image/jpeg", 
        "image/png", 
        "image/gif",
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    content_type = file.content_type
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {content_type} not allowed. Allowed types: PDF, JPEG, PNG, GIF, DOC, DOCX"
        )
    
    try:
        # Upload file
        file_url = await upload_document_file(file, "health_records")
        
        # Add attachment URL to health record
        success = await upload_health_record_attachment(
            file_url=file_url,
            record_id=record_id,
            owner_id=owner_id,
            request=request
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Health record not found or you don't have permission"
            )
        
        return {
            "message": "Attachment uploaded successfully",
            "file_url": file_url
        }
        
    except Exception as e:
        logger.error(f"Failed to upload attachment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload attachment: {str(e)}"
        ) 