from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class RecordType(str, Enum):
    VACCINATION = "vaccination"
    MEDICATION = "medication"
    VET_VISIT = "vet_visit"
    SURGERY = "surgery"
    ALLERGY = "allergy"
    TEST_RESULT = "test_result"
    WEIGHT = "weight"
    TREATMENT = "treatment"
    OTHER = "other"


class HealthRecordCreate(BaseModel):
    title: str
    record_type: RecordType
    date: date
    description: str
    provider_name: Optional[str] = None
    provider_contact: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None
    reminder_date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthRecordUpdate(BaseModel):
    title: Optional[str] = None
    record_type: Optional[RecordType] = None
    date: Optional[date] = None
    description: Optional[str] = None
    provider_name: Optional[str] = None
    provider_contact: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None
    reminder_date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthRecordOut(BaseModel):
    id: str
    pet_id: str
    pet_name: Optional[str] = None
    title: str
    record_type: RecordType
    date: date
    description: str
    provider_name: Optional[str] = None
    provider_contact: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None
    reminder_date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str


class VaccinationRecord(BaseModel):
    name: str
    date: date
    valid_until: Optional[date] = None
    provider: Optional[str] = None
    lot_number: Optional[str] = None
    certificate_url: Optional[str] = None 