from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ReportEntityType(str, Enum):
    USER = "user"
    PET = "pet"
    REVIEW = "review"
    MESSAGE = "message"
    LISTING = "listing"


class ReportStatusType(str, Enum):
    PENDING = "pending"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReportCreate(BaseModel):
    reason: str
    details: Optional[str] = None
    evidence_urls: Optional[list[str]] = None


class ReportOut(BaseModel):
    id: str
    reporter_id: str
    entity_id: str
    entity_type: ReportEntityType
    reason: str
    details: Optional[str] = None
    evidence_urls: Optional[list[str]] = None
    status: ReportStatusType
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    entity_data: Optional[Dict[str, Any]] = None


class ReportStatusUpdate(BaseModel):
    status: ReportStatusType
    admin_notes: Optional[str] = None 