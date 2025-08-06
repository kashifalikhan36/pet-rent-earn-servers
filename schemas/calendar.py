from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class BlockedDateReason(str, Enum):
    MAINTENANCE = "maintenance"
    PERSONAL = "personal"
    UNAVAILABLE = "unavailable"
    BOOKED = "booked"
    OTHER = "other"


class BlockedDateCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[BlockedDateReason] = BlockedDateReason.UNAVAILABLE
    notes: Optional[str] = None
    
    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class BlockedDateUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[BlockedDateReason] = None
    notes: Optional[str] = None


class BlockedDateOut(BaseModel):
    id: str
    pet_id: str
    start_date: date
    end_date: date
    reason: BlockedDateReason
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AvailabilityCheckResult(BaseModel):
    is_available: bool
    conflicting_dates: Optional[List[date]] = None
    blocked_reason: Optional[str] = None
    booking_ids: Optional[List[str]] = None


class PetCalendarItem(BaseModel):
    date: date
    status: str  # "available", "blocked", "booked"
    reason: Optional[str] = None
    booking_id: Optional[str] = None
    

class UserCalendarEvent(BaseModel):
    id: str
    pet_id: str
    pet_name: str
    pet_photo: Optional[str] = None
    start_date: date
    end_date: date
    event_type: str  # "booking" or "blocked"
    status: str  # For bookings: "pending", "confirmed", "canceled", "completed"
    with_user_id: Optional[str] = None
    with_user_name: Optional[str] = None
    price: Optional[float] = None
    notes: Optional[str] = None 