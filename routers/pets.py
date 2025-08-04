from fastapi import APIRouter, Depends, HTTPException, Request, status, File, Form, UploadFile, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from schemas.pet import (
    PetCreate, PetOut, PetUpdate, PetSearchFilters, PetPhotoOut,
    PetSearchResponse, PetStatusUpdate, ListingType, RentalType,
    PetAnalytics, PetReviewCreate, PetReviewOut
)
from schemas.user import OwnerProfileOut
from schemas.booking import AvailabilityResponse
from dependencies.auth import get_current_active_user
from crud.pet import (
    create_pet_listing, get_pet_by_id, get_user_pet_listings,
    update_pet_listing, delete_pet_listing, search_pets,
    get_featured_pets, upload_pet_photo, delete_pet_photo,
    add_pet_to_favorites, remove_pet_from_favorites, get_user_favorite_pets,
    get_pet_analytics, update_pet_status, get_nearby_pets,
    create_pet_review, get_pet_reviews
)
from crud.user import get_pet_owner_profile
from crud.booking import check_pet_availability
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


@router.get("/my-listings", response_model=List[PetOut])
async def get_my_pet_listings(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get current user's pet listings"""
    return await get_user_pet_listings(current_user["id"], request)


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
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    breed: str = Form(...),
    age: int = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    listingType: str = Form(...),
    price: Optional[float] = Form(None),
    dailyRate: Optional[float] = Form(None),
    rentalType: Optional[str] = Form(None),
    minRentalDays: Optional[int] = Form(None),
    maxRentalDays: Optional[int] = Form(None),
    availableFrom: Optional[str] = Form(None),
    availableTo: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    size: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    vaccinated: Optional[bool] = Form(False),
    spayedNeutered: Optional[bool] = Form(False),
    microchipped: Optional[bool] = Form(False),
    healthCertificate: Optional[bool] = Form(False),
    good_with_kids: Optional[bool] = Form(False),
    good_with_pets: Optional[bool] = Form(False),
    specialNeeds: Optional[str] = Form(None),
    photos: List[UploadFile] = File(...),
    current_user = Depends(get_current_active_user)
):
    """Create new pet listing with photos
    
    Accepts multipart/form-data with all pet fields and one or more photos.
    At least one photo is required.
    """
    try:
        # Validate at least one photo
        if not photos or len(photos) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one photo is required"
            )
            
        # Parse dates if provided
        available_from = None
        available_to = None
        
        if availableFrom:
            try:
                available_from = datetime.fromisoformat(availableFrom)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid availableFrom date format. Use ISO format (YYYY-MM-DD)"
                )
                
        if availableTo:
            try:
                available_to = datetime.fromisoformat(availableTo)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid availableTo date format. Use ISO format (YYYY-MM-DD)"
                )

        # Create pet data object
        pet_data = {
            "name": name,
            "type": type,
            "breed": breed,
            "age": age,
            "description": description,
            "location": location,
            "listingType": listingType,
            "gender": gender,
            "size": size,
            "color": color,
            "weight": weight,
            "vaccinated": vaccinated,
            "spayedNeutered": spayedNeutered,
            "microchipped": microchipped,
            "healthCertificate": healthCertificate,
            "good_with_kids": good_with_kids,
            "good_with_pets": good_with_pets,
            "specialNeeds": specialNeeds,
            "availableFrom": available_from,
            "availableTo": available_to,
        }
        
        # Add conditional fields based on listing type
        if listingType == "sale":
            if not price:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price is required for sale listings"
                )
            pet_data["price"] = price
        elif listingType == "rent":
            if not all([dailyRate, rentalType, minRentalDays, maxRentalDays]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="dailyRate, rentalType, minRentalDays, and maxRentalDays are required for rental listings"
                )
            pet_data["dailyRate"] = dailyRate
            pet_data["rentalType"] = rentalType
            pet_data["minRentalDays"] = minRentalDays
            pet_data["maxRentalDays"] = maxRentalDays
            
            # Validate rental days
            if int(minRentalDays) > int(maxRentalDays):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="minRentalDays cannot be greater than maxRentalDays"
                )
            
        # Create pet in database
        pet = await create_pet_listing(pet_data, current_user["id"], request)
        
        if not pet:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create pet listing"
            )
        
        # Upload all photos
        try:
            for i, file in enumerate(photos):
                # The first photo is primary
                is_primary = (i == 0)
                
                # Upload photo and associate with pet
                photo_data = {
                    "caption": f"{name} photo {i+1}",
                    "is_primary": is_primary
                }
                
                await upload_pet_photo(pet["id"], file, photo_data, current_user["id"], request)
                
        except Exception as e:
            logger.error(f"Error uploading pet photos: {str(e)}")
            # We won't fail the whole request if some photos fail to upload
            
        # Get updated pet with photos
        updated_pet = await get_pet_by_id(pet["id"], request)
        return updated_pet
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pet listing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pet listing"
        )


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
        # Create photo data
        photo_data = {
            "caption": caption,
            "is_primary": is_primary
        }
        
        # Add photo to pet
        photo = await upload_pet_photo(
            pet_id, file, photo_data, current_user["id"], request
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


@router.get("/{pet_id}/reviews", response_model=List[PetReviewOut])
async def get_pet_reviews_endpoint(
    pet_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50)
):
    """Get reviews for a pet"""
    skip = (page - 1) * per_page
    reviews = await get_pet_reviews(pet_id, request, skip, per_page)
    return reviews


@router.post("/{pet_id}/reviews", response_model=PetReviewOut)
async def create_pet_review_endpoint(
    pet_id: str,
    review: PetReviewCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create a review for a pet"""
    user_id = current_user["id"]
    user_name = current_user.get("name", "Anonymous User")
    user_avatar = current_user.get("avatar_url")
    
    created_review = await create_pet_review(
        pet_id, 
        review.dict(), 
        user_id, 
        user_name, 
        user_avatar, 
        request
    )
    
    if not created_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    return created_review 


@router.get("/{pet_id}/owner", response_model=OwnerProfileOut)
async def get_pet_owner_details(
    pet_id: str,
    request: Request
):
    """Get detailed owner profile for a pet"""
    owner_profile = await get_pet_owner_profile(pet_id, request)
    
    if not owner_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet or owner not found"
        )
    
    return owner_profile 


@router.get("/{pet_id}/availability", response_model=AvailabilityResponse)
async def check_pet_availability_endpoint(
    pet_id: str,
    start_date: date,
    end_date: date,
    request: Request
):
    """Check if pet is available for booking in the given date range"""
    try:
        # Check if pet exists
        pet = await get_pet_by_id(pet_id, request, increment_views=False)
        if not pet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pet not found"
            )
            
        # Verify dates
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
            
        # Check availability
        database = request.app.mongodb
        availability = await check_pet_availability(pet_id, start_date, end_date, database)
        
        return availability
        
    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check availability"
        ) 