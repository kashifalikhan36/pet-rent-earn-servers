from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    BOOKING_REQUEST = "booking_request"
    BOOKING_ACCEPTED = "booking_accepted"
    BOOKING_DECLINED = "booking_declined"
    BOOKING_CANCELED = "booking_canceled"
    BOOKING_COMPLETED = "booking_completed"
    MESSAGE_RECEIVED = "message_received"
    REVIEW_RECEIVED = "review_received"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    SYSTEM = "system"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    DISPUTE_CREATED = "dispute_created"
    DISPUTE_RESOLVED = "dispute_resolved"


class NotificationCreate(BaseModel):
    recipient_id: str
    type: NotificationType
    title: str
    message: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class NotificationOut(BaseModel):
    id: str
    recipient_id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    created_at: datetime
    read_at: Optional[datetime] = None
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationSettings(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    booking_updates: bool = True
    messages: bool = True
    reviews: bool = True
    payments: bool = True
    system_announcements: bool = True
    offers: bool = True
    disputes: bool = True


class NotificationSettingsUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    booking_updates: Optional[bool] = None
    messages: Optional[bool] = None
    reviews: Optional[bool] = None
    payments: Optional[bool] = None
    system_announcements: Optional[bool] = None
    offers: Optional[bool] = None
    disputes: Optional[bool] = None 