from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, File, UploadFile, Form
from typing import List, Dict, Any, Optional

from schemas.report import ReportCreate, ReportOut, ReportEntityType, ReportStatusType, ReportStatusUpdate
from dependencies.auth import get_current_active_user
from crud.report import (
    create_report, get_user_reports, get_report_by_id,
    update_report_status, get_all_reports, delete_report
)
from utils.file_upload import upload_image_file
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/users/{user_id}", response_model=ReportOut)
async def report_user(
    user_id: str,
    report_data: ReportCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Report a user for inappropriate behavior"""
    reporter_id = current_user["id"]
    
    # Ensure user is not reporting themselves
    if user_id == reporter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot report yourself"
        )
    
    report = await create_report(
        entity_id=user_id,
        entity_type=ReportEntityType.USER,
        reporter_id=reporter_id,
        reason=report_data.reason,
        details=report_data.details,
        evidence_urls=report_data.evidence_urls,
        request=request
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create report. You may have already reported this user or the user doesn't exist."
        )
    
    return report


@router.post("/pets/{pet_id}", response_model=ReportOut)
async def report_pet(
    pet_id: str,
    report_data: ReportCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Report a pet listing"""
    reporter_id = current_user["id"]
    
    report = await create_report(
        entity_id=pet_id,
        entity_type=ReportEntityType.PET,
        reporter_id=reporter_id,
        reason=report_data.reason,
        details=report_data.details,
        evidence_urls=report_data.evidence_urls,
        request=request
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create report. You may have already reported this pet or the pet doesn't exist."
        )
    
    return report


@router.post("/reviews/{review_id}", response_model=ReportOut)
async def report_review(
    review_id: str,
    report_data: ReportCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Report a review"""
    reporter_id = current_user["id"]
    
    report = await create_report(
        entity_id=review_id,
        entity_type=ReportEntityType.REVIEW,
        reporter_id=reporter_id,
        reason=report_data.reason,
        details=report_data.details,
        evidence_urls=report_data.evidence_urls,
        request=request
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create report. You may have already reported this review or the review doesn't exist."
        )
    
    return report


@router.post("/messages/{message_id}", response_model=ReportOut)
async def report_message(
    message_id: str,
    report_data: ReportCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Report a message"""
    reporter_id = current_user["id"]
    
    report = await create_report(
        entity_id=message_id,
        entity_type=ReportEntityType.MESSAGE,
        reporter_id=reporter_id,
        reason=report_data.reason,
        details=report_data.details,
        evidence_urls=report_data.evidence_urls,
        request=request
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create report. You may have already reported this message or the message doesn't exist."
        )
    
    return report


@router.get("/my-reports", response_model=List[ReportOut])
async def get_my_reports(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get reports submitted by current user"""
    user_id = current_user["id"]
    skip = (page - 1) * per_page
    
    reports = await get_user_reports(
        user_id=user_id,
        request=request,
        skip=skip,
        limit=per_page
    )
    
    return reports


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get a report by ID (only reporter or admin can view)"""
    user_id = current_user["id"]
    
    report = await get_report_by_id(
        report_id=report_id,
        user_id=user_id,
        request=request
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or you don't have permission to view it"
        )
    
    return report


@router.post("/evidence", response_model=Dict[str, Any])
async def upload_report_evidence(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_active_user)
):
    """Upload evidence images for a report"""
    # Check file types
    for file in files:
        content_type = file.content_type
        if not content_type or not content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not an image"
            )
    
    # Upload images
    image_urls = []
    for file in files:
        try:
            image_url = await upload_image_file(file, "reports")
            image_urls.append(image_url)
        except Exception as e:
            logger.error(f"Failed to upload report evidence: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload evidence: {str(e)}"
            )
    
    return {
        "message": f"{len(image_urls)} evidence files uploaded successfully",
        "evidence_urls": image_urls
    }


@router.delete("/{report_id}")
async def delete_report_endpoint(
    report_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete a report (only reporter or admin can delete)"""
    user_id = current_user["id"]
    
    success = await delete_report(
        report_id=report_id,
        user_id=user_id,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or you don't have permission to delete it"
        )
    
    return {"message": "Report deleted successfully"}


# Admin-only endpoints
@router.get("", response_model=Dict[str, Any])
async def get_all_reports_endpoint(
    request: Request,
    status: Optional[ReportStatusType] = None,
    entity_type: Optional[ReportEntityType] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get all reports with filters (admin only)"""
    # Check admin permission
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    skip = (page - 1) * per_page
    
    reports, total_count = await get_all_reports(
        request=request,
        status=status,
        entity_type=entity_type,
        skip=skip,
        limit=per_page
    )
    
    return {
        "reports": reports,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": (total_count + per_page - 1) // per_page  # Ceiling division
    }


@router.put("/{report_id}/status", response_model=ReportOut)
async def update_report_status_endpoint(
    report_id: str,
    status_update: ReportStatusUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update report status (admin only)"""
    admin_id = current_user["id"]
    
    updated_report = await update_report_status(
        report_id=report_id,
        status=status_update.status,
        admin_notes=status_update.admin_notes,
        admin_id=admin_id,
        request=request
    )
    
    if not updated_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or you don't have admin permission"
        )
    
    return updated_report 