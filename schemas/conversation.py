from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str
    attachment_urls: List[str] = []


class MessageOut(BaseModel):
    """Schema for message output."""
    id: str
    conversation_id: str  # Required field that was missing
    sender_id: str
    content: str
    read: bool = False
    attachment_urls: List[str] = []
    is_image_message: bool = False
    created_at: datetime


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""
    recipient_id: str
    message: str
    related_pet_id: Optional[str] = None
    related_booking_id: Optional[str] = None
    attachment_urls: List[str] = []


class ConversationOut(BaseModel):
    """Schema for conversation output."""
    id: str
    participants: List[str]
    last_message: Optional[Dict[str, Any]] = None
    unread_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    related_pet_id: Optional[str] = None
    related_booking_id: Optional[str] = None
    
    # Related data for convenience
    participant_details: Dict[str, Any] = Field(default_factory=dict)


class ConversationWithMessages(ConversationOut):
    """Schema for conversation with messages."""
    messages: List[MessageOut] = []


class ConversationSummary(BaseModel):
    """Schema for conversation summary in lists."""
    id: str
    other_participant_id: str
    other_participant_name: str
    other_participant_avatar: Optional[str] = None
    last_message_text: str
    last_message_time: datetime
    unread_count: int = 0
    related_pet_id: Optional[str] = None
    related_booking_id: Optional[str] = None


class ArchiveConversationRequest(BaseModel):
    """Schema for archiving a conversation."""
    archive: bool = True


class OfferStatus(str, Enum):
    """Enum for offer status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ConversationOfferCreate(BaseModel):
    """Schema for creating an offer in a conversation."""
    pet_id: str
    price: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_days: Optional[int] = None
    message: Optional[str] = None
    expire_after_hours: int = 24  # Offer expires after 24 hours by default


class ConversationOfferOut(BaseModel):
    """Schema for offer output."""
    id: str
    conversation_id: str
    sender_id: str
    pet_id: str
    price: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_days: Optional[int] = None
    message: Optional[str] = None
    status: OfferStatus
    created_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    
    # Pet and user details
    pet_details: Dict[str, Any] = Field(default_factory=dict)
    sender_details: Dict[str, Any] = Field(default_factory=dict)


class OfferResponse(BaseModel):
    """Schema for responding to an offer."""
    accept: bool
    message: Optional[str] = None 