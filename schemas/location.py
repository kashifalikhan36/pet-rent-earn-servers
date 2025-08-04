from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class LocationSchema(BaseModel):
    """Schema for location."""
    city: str
    state: Optional[str] = None
    country: str
    address: Optional[str] = None
    postal_code: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None  # [longitude, latitude]


class PopularLocation(BaseModel):
    """Schema for popular location."""
    city: str
    state: Optional[str] = None
    country: str
    count: int
    image_url: Optional[str] = None


class GeocodeRequest(BaseModel):
    """Schema for geocoding request."""
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class GeocodeResponse(BaseModel):
    """Schema for geocoding response."""
    formatted_address: str
    latitude: float
    longitude: float
    city: str
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None 