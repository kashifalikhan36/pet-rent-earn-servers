from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReviewType(str, Enum):
    USER = "user"
    PET = "pet"


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    comment: str
    attributes: Optional[Dict[str, int]] = None
    images: Optional[List[str]] = None
    anonymous: bool = False


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None
    attributes: Optional[Dict[str, int]] = None


class ReviewOut(BaseModel):
    id: str
    reviewer_id: str
    reviewer_name: str
    reviewer_avatar: Optional[str] = None
    entity_id: str
    entity_type: ReviewType
    rating: int
    title: Optional[str] = None
    comment: str
    attributes: Optional[Dict[str, int]] = None
    images: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    anonymous: bool = False
    transaction_id: Optional[str] = None
    helpful_count: int = 0
    reported: bool = False


class ReviewSummary(BaseModel):
    count: int = 0
    average_rating: float = 0.0
    rating_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    )
    attributes_avg: Optional[Dict[str, float]] = None


class ReviewFilter(BaseModel):
    min_rating: Optional[int] = Field(None, ge=1, le=5)
    max_rating: Optional[int] = Field(None, ge=1, le=5)
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"


class ReviewHelpful(BaseModel):
    helpful: bool


class ReviewReport(BaseModel):
    reason: str
    details: Optional[str] = None 