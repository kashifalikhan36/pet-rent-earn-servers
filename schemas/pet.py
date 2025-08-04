from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
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


class ListingType(str, Enum):
    RENT = "rent"
    SALE = "sale"
    FREE = "free"


class RentalType(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class LocationSchema(BaseModel):
    city: str
    state: Optional[str] = None
    country: str = "United States"
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
    # Basic information (always required)
    name: str = Field(..., min_length=1, max_length=100)
    type: PetSpecies = Field(..., description="Animal type")
    breed: str = Field(..., max_length=100)
    age: int = Field(..., ge=0, le=50)
    description: str = Field(..., min_length=10, max_length=2000)
    location: str = Field(..., description="City or location name")
    
    # Listing type (required)
    listingType: ListingType = Field(..., description="Type of listing: sale, rent, or free")
    
    # Conditional fields based on listing type
    price: Optional[float] = Field(None, ge=0, description="Sale price if listing type is 'sale'")
    dailyRate: Optional[float] = Field(None, ge=0, description="Cost per day if listing type is 'rent'")
    rentalType: Optional[RentalType] = Field(None, description="Hourly/daily/weekly rental type")
    minRentalDays: Optional[int] = Field(None, ge=1, le=365, description="Minimum rental period")
    maxRentalDays: Optional[int] = Field(None, ge=1, le=365, description="Maximum rental period")
    availableFrom: Optional[datetime] = Field(None, description="Start date of availability")
    availableTo: Optional[datetime] = Field(None, description="End date of availability")
    
    # Optional fields
    gender: Optional[Gender] = None
    size: Optional[str] = Field(None, pattern="^(small|medium|large)$")
    color: Optional[str] = Field(None, max_length=100)
    weight: Optional[float] = Field(None, ge=0, le=200)
    
    # Health and care (optional)
    vaccinated: Optional[bool] = None
    spayedNeutered: Optional[bool] = None
    microchipped: Optional[bool] = None
    healthCertificate: Optional[bool] = None
    good_with_kids: Optional[bool] = None
    good_with_pets: Optional[bool] = None
    specialNeeds: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('price')
    @classmethod
    def validate_price_for_sale(cls, v, info):
        values = info.data
        if 'listingType' in values and values['listingType'] == ListingType.SALE and v is None:
            raise ValueError('Price is required for sale listings')
        return v
        
    @field_validator('dailyRate', 'rentalType', 'minRentalDays', 'maxRentalDays')
    @classmethod
    def validate_rental_fields(cls, v, info):
        values = info.data
        if 'listingType' in values and values['listingType'] == ListingType.RENT:
            if v is None:
                raise ValueError(f'{info.field_name} is required for rental listings')
        return v
        
    @field_validator('maxRentalDays')
    @classmethod
    def validate_rental_days(cls, v, info):
        values = info.data
        if v is not None and 'minRentalDays' in values and values['minRentalDays'] is not None and v < values['minRentalDays']:
            raise ValueError('Maximum rental days must be greater than or equal to minimum rental days')
        return v


class PetUpdate(BaseModel):
    # Basic information 
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=50)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    location: Optional[str] = Field(None, description="City or location name")
    
    # Listing type
    listingType: Optional[ListingType] = Field(None, description="Type of listing: sale, rent, or free")
    
    # Conditional fields based on listing type
    price: Optional[float] = Field(None, ge=0, description="Sale price")
    dailyRate: Optional[float] = Field(None, ge=0, description="Cost per day")
    rentalType: Optional[RentalType] = Field(None, description="Hourly/daily/weekly rental type")
    minRentalDays: Optional[int] = Field(None, ge=1, le=365, description="Minimum rental period")
    maxRentalDays: Optional[int] = Field(None, ge=1, le=365, description="Maximum rental period")
    availableFrom: Optional[datetime] = Field(None, description="Start date of availability")
    availableTo: Optional[datetime] = Field(None, description="End date of availability")
    
    # Optional fields
    gender: Optional[Gender] = None
    size: Optional[str] = Field(None, pattern="^(small|medium|large)$")
    color: Optional[str] = Field(None, max_length=100)
    weight: Optional[float] = Field(None, ge=0, le=200)
    
    # Health and care
    vaccinated: Optional[bool] = None
    spayedNeutered: Optional[bool] = None
    microchipped: Optional[bool] = None
    healthCertificate: Optional[bool] = None
    good_with_kids: Optional[bool] = None
    good_with_pets: Optional[bool] = None
    specialNeeds: Optional[str] = Field(None, max_length=1000)
    
    # Status
    status: Optional[PetStatus] = None
    featured: Optional[bool] = None


class PetOut(BaseModel):
    id: str
    owner_id: str
    
    # Basic information
    name: str
    type: PetSpecies
    breed: str
    age: int
    description: str
    location: str
    
    # Listing type and pricing
    listingType: ListingType
    price: Optional[float] = None  # For sales
    dailyRate: Optional[float] = None  # For rentals
    rentalType: Optional[RentalType] = None
    minRentalDays: Optional[int] = None
    maxRentalDays: Optional[int] = None
    availableFrom: Optional[datetime] = None
    availableTo: Optional[datetime] = None
    
    # Status
    status: PetStatus
    featured: bool = False
    
    # Pet characteristics
    gender: Optional[Gender] = None
    size: Optional[str] = None
    color: Optional[str] = None
    weight: Optional[float] = None
    
    # Health and care
    vaccinated: Optional[bool] = None
    spayedNeutered: Optional[bool] = None
    microchipped: Optional[bool] = None
    healthCertificate: Optional[bool] = None
    good_with_kids: Optional[bool] = None
    good_with_pets: Optional[bool] = None
    specialNeeds: Optional[str] = None
    
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


class PetReview(BaseModel):
    rating: float = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: str = Field(..., min_length=3, max_length=1000)
    
    
class PetReviewCreate(PetReview):
    pass


class PetReviewOut(PetReview):
    id: str
    pet_id: str
    reviewer_id: str
    reviewer_name: str
    reviewer_avatar: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None 