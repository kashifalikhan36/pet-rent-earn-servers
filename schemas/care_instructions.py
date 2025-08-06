from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CareInstructionCategory(str, Enum):
    FEEDING = "feeding"
    WALKING = "walking"
    MEDICATION = "medication"
    GROOMING = "grooming"
    BEHAVIOR = "behavior"
    EMERGENCY = "emergency"
    GENERAL = "general"
    OTHER = "other"


class CareInstructionItem(BaseModel):
    title: str
    description: str
    category: CareInstructionCategory
    priority: int = Field(1, ge=1, le=5)  # 1 = low, 5 = high
    image_urls: Optional[List[str]] = None
    order: Optional[int] = None


class CareInstructionsCreate(BaseModel):
    general_notes: Optional[str] = None
    emergency_contact: Optional[str] = None
    vet_info: Optional[str] = None
    food_instructions: Optional[str] = None
    medication_instructions: Optional[str] = None
    exercise_instructions: Optional[str] = None
    grooming_instructions: Optional[str] = None
    behavior_notes: Optional[str] = None
    additional_instructions: Optional[List[CareInstructionItem]] = None


class CareInstructionsUpdate(BaseModel):
    general_notes: Optional[str] = None
    emergency_contact: Optional[str] = None
    vet_info: Optional[str] = None
    food_instructions: Optional[str] = None
    medication_instructions: Optional[str] = None
    exercise_instructions: Optional[str] = None
    grooming_instructions: Optional[str] = None
    behavior_notes: Optional[str] = None
    additional_instructions: Optional[List[CareInstructionItem]] = None


class CareInstructionsOut(BaseModel):
    id: str
    pet_id: str
    pet_name: Optional[str] = None
    pet_photo: Optional[str] = None
    general_notes: Optional[str] = None
    emergency_contact: Optional[str] = None
    vet_info: Optional[str] = None
    food_instructions: Optional[str] = None
    medication_instructions: Optional[str] = None
    exercise_instructions: Optional[str] = None
    grooming_instructions: Optional[str] = None
    behavior_notes: Optional[str] = None
    additional_instructions: Optional[List[CareInstructionItem]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None 