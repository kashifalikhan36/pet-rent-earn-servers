from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse

from schemas.pet import (
    PetCreate, PetUpdate, PetOut, PetSearchFilters, PetSearchResponse,
    PetPhotoUpload, PetPhotoOut, PetStatusUpdate, PetAnalytics
)
from dependencies.auth import get_current_active_user
from crud.pet import (
    create_pet_listing, get_pet_by_id, get_user_pet_listings,
    update_pet_listing, delete_pet_listing, search_pets,
    get_featured_pets, add_pet_to_favorites, remove_pet_from_favorites,
    get_user_favorite_pets, upload_pet_photo, delete_pet_photo,
    get_pet_analytics, update_pet_status, get_nearby_pets
)
from utils.file_upload import upload_image_file
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[PetOut])
async def get_all_pets(
    request: Request,
    species: Optional[str] = Query(None),
    breed: Optional[str] = Query(None),
    age_min: Optional[int] = Query(None, ge=0),
    age_max: Optional[int] = Query(None, ge=0),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    city: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    good_with_kids: Optional[bool] = Query(None),
    good_with_pets: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get all active pet listings with optional filters"""
    filters = {}
    
    if species:
        filters["species"] = species
    if breed:
        filters["breed"] = breed
    if age_min is not None:
        filters["age_min"] = age_min
    if age_max is not None:
        filters["age_max"] = age_max
    if price_min is not None:
        filters["price_min"] = price_min
    if price_max is not None:
        filters["price_max"] = price_max
    if city or country:
        filters["location"] = {}
        if city:
            filters["location"]["city"] = city
        if country:
            filters["location"]["country"] = country
    if good_with_kids is not None:
        filters["good_with_kids"] = good_with_kids
    if good_with_pets is not None:
        filters["good_with_pets"] = good_with_pets
    
    skip = (page - 1) * per_page
    pets = await search_pets(filters, request, skip, per_page)
    
    return pets


@router.get("/search", response_model=List[PetOut])
async def search_pet_listings(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    species: Optional[str] = Query(None),
    breed: Optional[str] = Query(None),
    age_min: Optional[int] = Query(None, ge=0),
    age_max: Optional[int] = Query(None, ge=0),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    city: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius: Optional[int] = Query(10, ge=1, le=100, description="Search radius in km"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Advanced search for pet listings"""
    filters = {}
    
    if q:
        # This would be a text search across name, breed, description
        filters["text_search"] = q
    if species:
        filters["species"] = species
    if breed:
        filters["breed"] = breed
    if age_min is not None:
        filters["age_min"] = age_min
    if age_max is not None:
        filters["age_max"] = age_max
    if price_min is not None:
        filters["price_min"] = price_min
    if price_max is not None:
        filters["price_max"] = price_max
    
    # Location-based search
    if latitude and longitude:
        filters["location"] = {
            "coordinates": [longitude, latitude]
        }
        filters["radius"] = radius * 1000  # Convert to meters
    elif city:
        filters["location"] = {"city": city}
    
    skip = (page - 1) * per_page
    pets = await search_pets(filters, request, skip, per_page)
    
    return pets


@router.get("/featured", response_model=List[PetOut])
async def get_featured_pet_listings(
    request: Request,
    limit: int = Query(10, ge=1, le=50)
):
    """Get featured pet listings"""
    return await get_featured_pets(request, limit)


@router.get("/nearby", response_model=List[PetOut])
async def get_pets_nearby(
    request: Request,
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"), 
    radius: int = Query(10, ge=1, le=100, description="Search radius in km"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get pets near a specific location"""
    return await get_nearby_pets(latitude, longitude, radius, request, limit)


@router.get("/{pet_id}", response_model=PetOut)
async def get_pet_details(pet_id: str, request: Request):
    """Get single pet details"""
    pet = await get_pet_by_id(pet_id, request, increment_views=True)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    return pet


@router.post("", response_model=PetOut)
async def create_pet(
    pet_data: PetCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create new pet listing"""
    pet = await create_pet_listing(pet_data, current_user["id"], request)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pet listing"
        )
    
    return pet


@router.put("/{pet_id}", response_model=PetOut)
async def update_pet(
    pet_id: str,
    pet_data: PetUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update pet listing"""
    pet = await update_pet_listing(pet_id, pet_data, current_user["id"], request)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to update it"
        )
    
    return pet


@router.delete("/{pet_id}")
async def delete_pet(
    pet_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete pet listing"""
    success = await delete_pet_listing(pet_id, current_user["id"], request)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to delete it"
        )
    
    return {"detail": "Pet listing deleted successfully"}


@router.post("/{pet_id}/photos", response_model=PetPhotoOut)
async def upload_pet_photos(
    pet_id: str,
    request: Request,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    current_user = Depends(get_current_active_user)
):
    """Upload pet photos"""
    try:
        # Upload file and get URL
        file_url = await upload_image_file(file, "pets")
        
        # Add photo to pet
        photo = await upload_pet_photo(
            pet_id, file_url, current_user["id"], request, caption, is_primary
        )
        
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pet not found or you don't have permission to upload photos"
            )
        
        return {
            "id": photo["id"],
            "pet_id": pet_id,
            "url": photo["url"],
            "caption": photo["caption"],
            "is_primary": photo["is_primary"],
            "uploaded_at": photo["uploaded_at"]
        }
        
    except Exception as e:
        logger.error(f"Error uploading pet photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload photo"
        )


@router.delete("/{pet_id}/photos/{photo_id}")
async def delete_pet_photo_endpoint(
    pet_id: str,
    photo_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete pet photo"""
    success = await delete_pet_photo(pet_id, photo_id, current_user["id"], request)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet or photo not found, or you don't have permission"
        )
    
    return {"detail": "Photo deleted successfully"}


@router.post("/{pet_id}/favorite")
async def add_pet_to_favorites_endpoint(
    pet_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Add pet to favorites"""
    success = await add_pet_to_favorites(current_user["id"], pet_id, request)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    return {"detail": "Pet added to favorites"}


@router.delete("/{pet_id}/favorite")
async def remove_pet_from_favorites_endpoint(
    pet_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Remove pet from favorites"""
    success = await remove_pet_from_favorites(current_user["id"], pet_id, request)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found in favorites"
        )
    
    return {"detail": "Pet removed from favorites"}


@router.put("/{pet_id}/status", response_model=PetOut)
async def update_pet_status_endpoint(
    pet_id: str,
    status_data: PetStatusUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update pet listing status"""
    pet = await update_pet_status(pet_id, status_data.status, current_user["id"], request)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to update it"
        )
    
    return pet


@router.get("/{pet_id}/analytics", response_model=PetAnalytics)
async def get_pet_analytics_endpoint(
    pet_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get pet listing analytics"""
    analytics = await get_pet_analytics(pet_id, current_user["id"], request)
    
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to view analytics"
        )
    
    return analytics


# User-specific endpoints
@router.get("/users/{user_id}/listings", response_model=List[PetOut])
async def get_user_pet_listings_endpoint(
    user_id: str,
    request: Request
):
    """Get user's pet listings (public)"""
    return await get_user_pet_listings(user_id, request)


@router.get("/users/{user_id}/favorites", response_model=List[PetOut])
async def get_user_favorites_endpoint(
    user_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get user's favorite pets (only own favorites)"""
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own favorites"
        )
    
    return await get_user_favorite_pets(user_id, request) 