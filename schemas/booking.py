from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    """Booking status enum."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


class PaymentStatus(str, Enum):
    """Payment status enum."""
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    FAILED = "failed"


class BookingCreate(BaseModel):
    """Schema for booking creation."""
    pet_id: str
    start_date: date
    end_date: date
    message: Optional[str] = None
    pickup_time: Optional[str] = None  # HH:MM format
    dropoff_time: Optional[str] = None  # HH:MM format
    special_requests: Optional[str] = None


class BookingOut(BaseModel):
    """Schema for booking output."""
    id: str
    pet_id: str
    renter_id: str
    owner_id: str
    start_date: date
    end_date: date
    total_days: int
    daily_rate: float
    total_amount: float
    service_fee: float
    grand_total: float
    status: BookingStatus
    payment_status: PaymentStatus
    message: Optional[str] = None
    pickup_time: Optional[str] = None
    dropoff_time: Optional[str] = None
    special_requests: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related data for convenience
    pet: Dict[str, Any] = Field(default_factory=dict)
    owner: Dict[str, Any] = Field(default_factory=dict)
    renter: Dict[str, Any] = Field(default_factory=dict)


class BookingUpdate(BaseModel):
    """Schema for booking update."""
    status: Optional[BookingStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    special_requests: Optional[str] = None
    pickup_time: Optional[str] = None
    dropoff_time: Optional[str] = None


class AvailabilityCheck(BaseModel):
    """Schema for checking pet availability."""
    pet_id: str
    start_date: date
    end_date: date


class AvailabilityResponse(BaseModel):
    """Schema for availability response."""
    available: bool
    conflicting_bookings: List[Dict[str, Any]] = []
    available_dates: List[date] = []


class BookingSummary(BaseModel):
    """Schema for booking summary in lists."""
    id: str
    pet_name: str
    pet_image_url: Optional[str] = None
    owner_name: str
    owner_id: str
    renter_name: str
    renter_id: str
    status: BookingStatus
    start_date: date
    end_date: date
    total_amount: float
    created_at: datetime


class PaymentMethod(BaseModel):
    """Schema for payment method."""
    id: str
    type: str  # credit_card, paypal, etc.
    last_four: Optional[str] = None  # Last 4 digits if card
    expiry: Optional[str] = None  # MM/YY format if card
    is_default: bool = False 