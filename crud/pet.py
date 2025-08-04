from typing import Optional, List, Dict, Any
from fastapi import Request
from models.pet import PetModel
from schemas.pet import PetCreate, PetUpdate
import uuid
from datetime import datetime


async def create_pet_listing(pet_data: PetCreate, owner_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Create a new pet listing"""
    database = request.app.mongodb
    
    # Convert to dict and add owner info
    pet_dict = pet_data.dict()
    pet_dict["owner_id"] = owner_id
    pet_dict["status"] = "active"
    pet_dict["featured"] = False
    pet_dict["photos"] = []
    pet_dict["view_count"] = 0
    pet_dict["favorite_count"] = 0
    pet_dict["review_count"] = 0
    pet_dict["average_rating"] = None
    
    return await PetModel.create_pet(pet_dict, database)


async def get_pet_by_id(pet_id: str, request: Request, increment_views: bool = True) -> Optional[Dict[str, Any]]:
    """Get pet by ID with optional view count increment"""
    database = request.app.mongodb
    
    pet = await PetModel.get_pet_by_id(pet_id, database)
    
    if pet and increment_views:
        await PetModel.increment_view_count(pet_id, database)
        # Update the view count in the returned pet
        pet["view_count"] = pet.get("view_count", 0) + 1
    
    return pet


async def get_user_pet_listings(user_id: str, request: Request) -> List[Dict[str, Any]]:
    """Get all pet listings for a user"""
    database = request.app.mongodb
    return await PetModel.get_pets_by_owner(user_id, database)


async def update_pet_listing(pet_id: str, pet_data: PetUpdate, owner_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Update pet listing (only by owner)"""
    database = request.app.mongodb
    
    # First check if pet exists and is owned by user
    existing_pet = await PetModel.get_pet_by_id(pet_id, database)
    if not existing_pet or existing_pet["owner_id"] != owner_id:
        return None
    
    # Convert to dict and exclude None values
    update_dict = {k: v for k, v in pet_data.dict().items() if v is not None}
    
    if not update_dict:
        return existing_pet
    
    return await PetModel.update_pet(pet_id, update_dict, database)


async def delete_pet_listing(pet_id: str, owner_id: str, request: Request) -> bool:
    """Delete pet listing (only by owner)"""
    database = request.app.mongodb
    
    # First check if pet exists and is owned by user
    existing_pet = await PetModel.get_pet_by_id(pet_id, database)
    if not existing_pet or existing_pet["owner_id"] != owner_id:
        return False
    
    return await PetModel.delete_pet(pet_id, database)


async def search_pets(
    filters: Dict[str, Any], 
    request: Request, 
    skip: int = 0, 
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search pets with filters"""
    database = request.app.mongodb
    return await PetModel.search_pets(filters, database, skip, limit)


async def get_featured_pets(request: Request, limit: int = 10) -> List[Dict[str, Any]]:
    """Get featured pet listings"""
    database = request.app.mongodb
    return await PetModel.get_featured_pets(database, limit)


async def add_pet_to_favorites(user_id: str, pet_id: str, request: Request) -> bool:
    """Add pet to user's favorites"""
    database = request.app.mongodb
    
    # Check if pet exists
    pet = await PetModel.get_pet_by_id(pet_id, database)
    if not pet:
        return False
    
    success = await PetModel.add_to_favorites(user_id, pet_id, database)
    
    # Update favorite count
    if success:
        await database.pets.update_one(
            {"_id": pet["_id"]},
            {"$inc": {"favorite_count": 1}}
        )
    
    return success


async def remove_pet_from_favorites(user_id: str, pet_id: str, request: Request) -> bool:
    """Remove pet from user's favorites"""
    database = request.app.mongodb
    
    success = await PetModel.remove_from_favorites(user_id, pet_id, database)
    
    # Update favorite count
    if success:
        await database.pets.update_one(
            {"_id": pet_id},
            {"$inc": {"favorite_count": -1}}
        )
    
    return success


async def get_user_favorite_pets(user_id: str, request: Request) -> List[Dict[str, Any]]:
    """Get user's favorite pets"""
    database = request.app.mongodb
    return await PetModel.get_user_favorites(user_id, database)


async def upload_pet_photo(pet_id: str, file_url: str, owner_id: str, request: Request, caption: str = None, is_primary: bool = False) -> Optional[Dict[str, Any]]:
    """Add photo to pet listing"""
    database = request.app.mongodb
    
    # Check if pet exists and is owned by user
    pet = await PetModel.get_pet_by_id(pet_id, database)
    if not pet or pet["owner_id"] != owner_id:
        return None
    
    # Create photo object
    photo = {
        "id": str(uuid.uuid4()),
        "url": file_url,
        "caption": caption,
        "is_primary": is_primary,
        "uploaded_at": datetime.utcnow()
    }
    
    # If this is primary, unset other primary photos
    if is_primary:
        await database.pets.update_one(
            {"_id": pet["_id"]},
            {"$set": {"photos.$[].is_primary": False}}
        )
    
    # Add photo to pet
    result = await database.pets.update_one(
        {"_id": pet["_id"]},
        {"$push": {"photos": photo}}
    )
    
    if result.modified_count > 0:
        return photo
    return None


async def delete_pet_photo(pet_id: str, photo_id: str, owner_id: str, request: Request) -> bool:
    """Delete photo from pet listing"""
    database = request.app.mongodb
    
    # Check if pet exists and is owned by user
    pet = await PetModel.get_pet_by_id(pet_id, database)
    if not pet or pet["owner_id"] != owner_id:
        return False
    
    # Remove photo
    result = await database.pets.update_one(
        {"_id": pet["_id"]},
        {"$pull": {"photos": {"id": photo_id}}}
    )
    
    return result.modified_count > 0


async def get_pet_analytics(pet_id: str, owner_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Get analytics for a pet listing"""
    database = request.app.mongodb
    
    # Check if pet exists and is owned by user
    pet = await PetModel.get_pet_by_id(pet_id, database)
    if not pet or pet["owner_id"] != owner_id:
        return None
    
    # Get additional analytics data
    # (This would integrate with transaction and booking data when those are implemented)
    analytics = {
        "pet_id": pet_id,
        "view_count": pet.get("view_count", 0),
        "favorite_count": pet.get("favorite_count", 0),
        "inquiry_count": 0,  # TODO: Implement when messaging is added
        "booking_count": 0,  # TODO: Implement when transactions are added
        "average_rating": pet.get("average_rating"),
        "review_count": pet.get("review_count", 0),
        "total_earnings": 0.0,  # TODO: Implement when transactions are added
        "last_30_days_views": 0,  # TODO: Implement analytics tracking
        "last_30_days_bookings": 0  # TODO: Implement analytics tracking
    }
    
    return analytics


async def update_pet_status(pet_id: str, status: str, owner_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Update pet listing status"""
    database = request.app.mongodb
    
    # Check if pet exists and is owned by user
    pet = await PetModel.get_pet_by_id(pet_id, database)
    if not pet or pet["owner_id"] != owner_id:
        return None
    
    return await PetModel.update_pet(pet_id, {"status": status}, database)


async def get_nearby_pets(latitude: float, longitude: float, radius_km: int, request: Request, limit: int = 20) -> List[Dict[str, Any]]:
    """Get pets near a location"""
    database = request.app.mongodb
    
    filters = {
        "location": {
            "coordinates": [longitude, latitude]
        },
        "radius": radius_km * 1000  # Convert to meters
    }
    
    return await PetModel.search_pets(filters, database, 0, limit) 