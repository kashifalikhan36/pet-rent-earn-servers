from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str
    attachment_urls: List[str] = []


class MessageOut(BaseModel):
    """Schema for message output."""
    id: str
    conversation_id: str
    sender_id: str
    content: str
    read: bool = False
    attachment_urls: List[str] = []
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