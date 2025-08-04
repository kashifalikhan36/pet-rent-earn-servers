from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Dict, Any, Optional

from schemas.booking import (
    BookingCreate, BookingOut, BookingUpdate, BookingStatus,
    BookingSummary
)
from dependencies.auth import get_current_active_user
from crud.booking import (
    create_booking, get_booking, update_booking_status, get_user_bookings
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=BookingOut)
async def create_booking_endpoint(
    booking_data: BookingCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create a new booking request"""
    booking = await create_booking(
        booking_data=booking_data,
        renter_id=current_user["id"],
        request=request
    )
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create booking. Pet may not be available for the selected dates."
        )
        
    return booking


@router.get("", response_model=List[BookingSummary])
async def get_user_bookings_endpoint(
    request: Request,
    as_owner: Optional[bool] = Query(None, description="Filter by owner/renter role"),
    status: Optional[str] = Query(None, description="Filter by booking status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get list of user's bookings"""
    bookings, _ = await get_user_bookings(
        user_id=current_user["id"],
        request=request,
        as_owner=as_owner,
        status=status,
        page=page,
        limit=per_page
    )
    
    return bookings


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking_endpoint(
    booking_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get a specific booking"""
    booking = await get_booking(
        booking_id=booking_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found or you don't have access"
        )
        
    return booking


@router.put("/{booking_id}/status", response_model=BookingOut)
async def update_booking_status_endpoint(
    booking_id: str,
    status_update: BookingUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update booking status"""
    if not status_update.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
        
    booking = await update_booking_status(
        booking_id=booking_id,
        status=status_update.status,
        user_id=current_user["id"],
        request=request
    )
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found, you don't have permission, or status update is not allowed"
        )
        
    return booking 