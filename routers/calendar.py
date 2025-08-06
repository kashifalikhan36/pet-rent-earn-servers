from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta

from schemas.calendar import (
    BlockedDateCreate, BlockedDateOut, BlockedDateUpdate, BlockedDateReason,
    AvailabilityCheckResult, PetCalendarItem, UserCalendarEvent
)
from dependencies.auth import get_current_active_user
from crud.calendar import (
    create_blocked_date, update_blocked_date, delete_blocked_date,
    get_pet_calendar, get_user_schedule, check_date_availability
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/pets/{pet_id}", response_model=Dict[str, Any])
async def get_pet_calendar_endpoint(
    pet_id: str,
    start_date: date = Query(..., description="Start date for calendar"),
    end_date: date = Query(..., description="End date for calendar"),
    request: Request = None
):
    """
    Get calendar data for a pet
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Limit to 90 days
    date_diff = (end_date - start_date).days
    if date_diff > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 90 days"
        )
    
    calendar = await get_pet_calendar(
        pet_id=pet_id,
        start_date=start_date,
        end_date=end_date,
        request=request
    )
    
    if not calendar.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=calendar.get("message", "Failed to get calendar")
        )
    
    return calendar


@router.post("/pets/{pet_id}/blocked-dates", response_model=Dict[str, Any])
async def create_blocked_date_endpoint(
    pet_id: str,
    blocked_date: BlockedDateCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """
    Block dates for a pet
    """
    # Validate date range
    if blocked_date.start_date > blocked_date.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    result = await create_blocked_date(
        pet_id=pet_id,
        owner_id=current_user["id"],
        start_date=blocked_date.start_date,
        end_date=blocked_date.end_date,
        reason=blocked_date.reason,
        notes=blocked_date.notes,
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to update it"
        )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to block dates")
        )
    
    return result


@router.put("/blocked-dates/{block_id}", response_model=Dict[str, Any])
async def update_blocked_date_endpoint(
    block_id: str,
    update_data: BlockedDateUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """
    Update a blocked date
    """
    result = await update_blocked_date(
        block_id=block_id,
        owner_id=current_user["id"],
        update_data=update_data.dict(exclude_unset=True),
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blocked date not found or you don't have permission to update it"
        )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update blocked date")
        )
    
    return result


@router.delete("/blocked-dates/{block_id}", response_model=Dict[str, Any])
async def delete_blocked_date_endpoint(
    block_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """
    Delete a blocked date
    """
    result = await delete_blocked_date(
        block_id=block_id,
        owner_id=current_user["id"],
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blocked date not found or you don't have permission to delete it"
        )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to delete blocked date")
        )
    
    return result


@router.get("/my-schedule", response_model=List[Dict[str, Any]])
async def get_my_schedule_endpoint(
    start_date: date = Query(..., description="Start date for schedule"),
    end_date: date = Query(..., description="End date for schedule"),
    as_owner: Optional[bool] = Query(None, description="Filter by owner/renter role"),
    request: Request = None,
    current_user = Depends(get_current_active_user)
):
    """
    Get user's schedule
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Limit to 90 days
    date_diff = (end_date - start_date).days
    if date_diff > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 90 days"
        )
    
    schedule = await get_user_schedule(
        user_id=current_user["id"],
        start_date=start_date,
        end_date=end_date,
        request=request,
        as_owner=as_owner
    )
    
    return schedule


@router.get("/availability/{pet_id}", response_model=AvailabilityCheckResult)
async def check_availability_endpoint(
    pet_id: str,
    start_date: date = Query(..., description="Start date for check"),
    end_date: date = Query(..., description="End date for check"),
    request: Request = None
):
    """
    Check if a pet is available for booking in the given date range
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Check availability
    availability = await check_date_availability(
        pet_id=pet_id,
        start_date=start_date,
        end_date=end_date,
        request=request
    )
    
    return availability 