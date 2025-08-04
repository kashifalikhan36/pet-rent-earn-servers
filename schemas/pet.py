from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class PetSpecies(str, Enum):
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    FISH = "fish"
    RABBIT = "rabbit"
    HAMSTER = "hamster"
    GUINEA_PIG = "guinea_pig"
    REPTILE = "reptile"
    OTHER = "other"


class PetStatus(str, Enum):
    ACTIVE = "active"
    RENTED = "rented"
    INACTIVE = "inactive"
    SOLD = "sold"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class LocationSchema(BaseModel):
    city: str
    state: Optional[str] = None
    country: str
    address: Optional[str] = None
    coordinates: Optional[List[float]] = None  # [longitude, latitude]
    postal_code: Optional[str] = None


class PetPhotoSchema(BaseModel):
    id: str
    url: str
    caption: Optional[str] = None
    is_primary: bool = False
    uploaded_at: datetime


class PetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    species: PetSpecies
    breed: str = Field(..., max_length=100)
    age: int = Field(..., ge=0, le=50)
    gender: Gender
    description: str = Field(..., min_length=10, max_length=2000)
    daily_rate: float = Field(..., ge=0, le=10000)
    location: LocationSchema
    
    # Pet characteristics
    size: Optional[str] = Field(None, pattern="^(tiny|small|medium|large|giant)$")
    weight: Optional[float] = Field(None, ge=0, le=200)
    color: Optional[str] = Field(None, max_length=100)
    
    # Health and care
    vaccinated: bool = True
    spayed_neutered: bool = False
    house_trained: bool = True
    good_with_kids: bool = True
    good_with_pets: bool = True
    energy_level: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    
    # Requirements
    special_requirements: Optional[str] = Field(None, max_length=500)
    minimum_rental_days: int = Field(1, ge=1, le=365)
    maximum_rental_days: int = Field(30, ge=1, le=365)
    
    # Additional info
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    
    @validator('maximum_rental_days')
    def validate_rental_days(cls, v, values):
        if 'minimum_rental_days' in values and v < values['minimum_rental_days']:
            raise ValueError('Maximum rental days must be greater than or equal to minimum rental days')
        return v


class PetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    daily_rate: Optional[float] = Field(None, ge=0, le=10000)
    status: Optional[PetStatus] = None
    
    # Pet characteristics
    size: Optional[str] = Field(None, pattern="^(tiny|small|medium|large|giant)$")
    weight: Optional[float] = Field(None, ge=0, le=200)
    color: Optional[str] = Field(None, max_length=100)
    
    # Health and care
    vaccinated: Optional[bool] = None
    spayed_neutered: Optional[bool] = None
    house_trained: Optional[bool] = None
    good_with_kids: Optional[bool] = None
    good_with_pets: Optional[bool] = None
    energy_level: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    
    # Requirements
    special_requirements: Optional[str] = Field(None, max_length=500)
    minimum_rental_days: Optional[int] = Field(None, ge=1, le=365)
    maximum_rental_days: Optional[int] = Field(None, ge=1, le=365)
    
    # Additional info
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    featured: Optional[bool] = None


class PetOut(BaseModel):
    id: str
    owner_id: str
    name: str
    species: PetSpecies
    breed: str
    age: int
    gender: Gender
    description: str
    daily_rate: float
    status: PetStatus
    location: LocationSchema
    
    # Pet characteristics
    size: Optional[str] = None
    weight: Optional[float] = None
    color: Optional[str] = None
    
    # Health and care
    vaccinated: bool = True
    spayed_neutered: bool = False
    house_trained: bool = True
    good_with_kids: bool = True
    good_with_pets: bool = True
    energy_level: Optional[str] = None
    
    # Requirements
    special_requirements: Optional[str] = None
    minimum_rental_days: int = 1
    maximum_rental_days: int = 30
    
    # Additional info
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    featured: bool = False
    
    # Metadata
    photos: List[PetPhotoSchema] = []
    view_count: int = 0
    favorite_count: int = 0
    average_rating: Optional[float] = None
    review_count: int = 0
    
    created_at: datetime
    updated_at: datetime
    last_viewed_at: Optional[datetime] = None


class PetSearchFilters(BaseModel):
    species: Optional[PetSpecies] = None
    breed: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    size: Optional[str] = Field(None, pattern="^(tiny|small|medium|large|giant)$")
    location: Optional[Dict[str, Any]] = None
    radius: Optional[int] = Field(None, ge=1, le=100)  # km
    good_with_kids: Optional[bool] = None
    good_with_pets: Optional[bool] = None
    energy_level: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class PetSearchResponse(BaseModel):
    pets: List[PetOut]
    total_count: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class PetPhotoUpload(BaseModel):
    caption: Optional[str] = Field(None, max_length=200)
    is_primary: bool = False


class PetPhotoOut(BaseModel):
    id: str
    pet_id: str
    url: str
    caption: Optional[str] = None
    is_primary: bool = False
    uploaded_at: datetime


class PetStatusUpdate(BaseModel):
    status: PetStatus


class PetAnalytics(BaseModel):
    pet_id: str
    view_count: int
    favorite_count: int
    inquiry_count: int
    booking_count: int
    average_rating: Optional[float] = None
    review_count: int
    total_earnings: float = 0.0
    last_30_days_views: int = 0
    last_30_days_bookings: int = 0 