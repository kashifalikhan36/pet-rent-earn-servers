from typing import Optional, List, Dict, Any
from fastapi import Request
from models.pet import PetModel
from schemas.pet import PetCreate, PetUpdate
import uuid
from datetime import datetime
from core.config import get_settings

settings = get_settings()

def add_photo_base_url(pet: Dict[str, Any]) -> Dict[str, Any]:
    """Add base URL to photo URLs in pet data"""
    if pet and "photos" in pet and pet["photos"]:
        for photo in pet["photos"]:
            if "url" in photo and photo["url"].startswith("/"):
                photo["url"] = f"{settings.API_BASE_URL}{photo['url']}"
    return pet


def add_photo_base_urls(pets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add base URL to photo URLs in a list of pets"""
    return [add_photo_base_url(pet) for pet in pets]


async def create_pet_listing(pet_data, owner_id, request) -> Dict[str, Any]:
    """
    Create a new pet listing in the database.
    
    Args:
        pet_data: Dictionary or Pydantic model with pet data
        owner_id: ID of the pet owner
        request: FastAPI request object with database access
        
    Returns:
        Created pet object or None if failed
    """
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Convert to dict if it's a Pydantic model
        if hasattr(pet_data, "dict"):
            pet_dict = pet_data.dict()
        else:
            pet_dict = dict(pet_data)
            
        # Set default values
        now = datetime.utcnow()
        
        # Create database document
        pet_document = {
            "owner_id": owner_id,
            "name": pet_dict.get("name"),
            "type": pet_dict.get("type"),
            "breed": pet_dict.get("breed"),
            "age": int(pet_dict.get("age", 0)),
            "description": pet_dict.get("description"),
            "gender": pet_dict.get("gender"),
            "location": pet_dict.get("location"),
            
            # Listing type and pricing
            "listingType": pet_dict.get("listingType", "rent"),
            "price": float(pet_dict.get("price", 0)) if pet_dict.get("price") else None,
            "dailyRate": float(pet_dict.get("dailyRate", 0)) if pet_dict.get("dailyRate") else None,
            "rentalType": pet_dict.get("rentalType"),
            "minRentalDays": int(pet_dict.get("minRentalDays", 1)) if pet_dict.get("minRentalDays") else None,
            "maxRentalDays": int(pet_dict.get("maxRentalDays", 30)) if pet_dict.get("maxRentalDays") else None,
            
            # Dates
            "availableFrom": pet_dict.get("availableFrom"),
            "availableTo": pet_dict.get("availableTo"),
            
            # Pet characteristics
            "size": pet_dict.get("size"),
            "weight": float(pet_dict.get("weight")) if pet_dict.get("weight") else None,
            "color": pet_dict.get("color"),
            
            # Health and care
            "vaccinated": bool(pet_dict.get("vaccinated", False)),
            "spayedNeutered": bool(pet_dict.get("spayedNeutered", False)),
            "microchipped": bool(pet_dict.get("microchipped", False)),
            "healthCertificate": bool(pet_dict.get("healthCertificate", False)),
            "good_with_kids": bool(pet_dict.get("good_with_kids", False)),
            "good_with_pets": bool(pet_dict.get("good_with_pets", False)),
            "specialNeeds": pet_dict.get("specialNeeds"),
            
            # Status and metadata
            "status": "active",
            "featured": False,
            "view_count": 0,
            "favorite_count": 0,
            "photos": [],  # Initialize photos array
            "created_at": now,
            "updated_at": now
        }
        
        # Insert pet into database
        result = await database.pets.insert_one(pet_document)
        pet_id = str(result.inserted_id)
        
        # Get the inserted pet with photos base URL added
        pet = await get_pet_by_id(pet_id, request, increment_views=False)
        return pet
        
    except Exception as e:
        print(f"Error creating pet listing: {str(e)}")
        return None


async def get_pet_by_id(pet_id: str, request: Request, increment_views: bool = True) -> Optional[Dict[str, Any]]:
    """Get pet by ID with optional view count increment"""
    database = request.app.mongodb
    
    pet = await PetModel.get_pet_by_id(pet_id, database)
    
    if pet and increment_views:
        await PetModel.increment_view_count(pet_id, database)
        # Update the view count in the returned pet
        pet["view_count"] = pet.get("view_count", 0) + 1
    
    return add_photo_base_url(pet)


async def get_user_pet_listings(user_id: str, request: Request) -> List[Dict[str, Any]]:
    """Get all pet listings for a user"""
    database = request.app.mongodb
    pets = await PetModel.get_pets_by_owner(user_id, database)
    return add_photo_base_urls(pets)


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
        return add_photo_base_url(existing_pet)
    
    updated_pet = await PetModel.update_pet(pet_id, update_dict, database)
    return add_photo_base_url(updated_pet)


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
    pets = await PetModel.search_pets(filters, database, skip, limit)
    return add_photo_base_urls(pets)


async def get_featured_pets(request: Request, limit: int = 10) -> List[Dict[str, Any]]:
    """Get featured pet listings"""
    database = request.app.mongodb
    pets = await PetModel.get_featured_pets(database, limit)
    return add_photo_base_urls(pets)


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
    pets = await PetModel.get_user_favorites(user_id, database)
    return add_photo_base_urls(pets)


async def upload_pet_photo(pet_id: str, file, photo_data, owner_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Add photo to pet listing
    
    Args:
        pet_id: ID of the pet
        file: UploadFile object containing the image
        photo_data: Dictionary with caption and is_primary flag
        owner_id: ID of the pet owner
        request: FastAPI request object
        
    Returns:
        Photo object or None if failed
    """
    database = request.app.mongodb
    from bson import ObjectId
    
    try:
        # Check if pet exists and is owned by user
        pet = await get_pet_by_id(pet_id, request, increment_views=False)
        if not pet or pet["owner_id"] != owner_id:
            return None
        
        # Upload file and get URL
        from utils.file_upload import upload_image_file
        file_url = await upload_image_file(file, "pets")
        
        if not file_url:
            return None
            
        # Extract photo data
        caption = photo_data.get("caption") if isinstance(photo_data, dict) else None
        is_primary = photo_data.get("is_primary", False) if isinstance(photo_data, dict) else False
        
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
                {"_id": ObjectId(pet_id)},
                {"$set": {"photos.$[].is_primary": False}}
            )
        
        # Add photo to pet
        result = await database.pets.update_one(
            {"_id": ObjectId(pet_id)},
            {"$push": {"photos": photo}}
        )
        
        if result.modified_count > 0:
            # Add base URL to the photo URL
            photo["url"] = f"{settings.API_BASE_URL}{photo['url']}"
            return photo
        return None
        
    except Exception as e:
        print(f"Error uploading pet photo: {str(e)}")
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
    pet = await get_pet_by_id(pet_id, request, increment_views=False)
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
    
    updated_pet = await PetModel.update_pet(pet_id, {"status": status}, database)
    return add_photo_base_url(updated_pet)


async def get_nearby_pets(latitude: float, longitude: float, radius_km: int, request: Request, limit: int = 20) -> List[Dict[str, Any]]:
    """Get pets near a location"""
    database = request.app.mongodb
    
    filters = {
        "location": {
            "coordinates": [longitude, latitude]
        },
        "radius": radius_km * 1000  # Convert to meters
    }
    
    pets = await PetModel.search_pets(filters, database, 0, limit)
    return add_photo_base_urls(pets) 

async def create_pet_review(pet_id: str, review_data: dict, user_id: str, user_name: str, user_avatar: str, request: Request) -> Optional[Dict[str, Any]]:
    """Create a review for a pet"""
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Check if pet exists
        pet = await PetModel.get_pet_by_id(pet_id, database)
        if not pet:
            return None
            
        # Check if user already reviewed this pet
        existing_review = await database.pet_reviews.find_one({
            "pet_id": pet_id,
            "reviewer_id": user_id
        })
        
        if existing_review:
            # Update existing review
            now = datetime.utcnow()
            await database.pet_reviews.update_one(
                {"_id": existing_review["_id"]},
                {
                    "$set": {
                        "rating": review_data["rating"],
                        "comment": review_data["comment"],
                        "updated_at": now
                    }
                }
            )
            
            # Get the updated review
            review = await database.pet_reviews.find_one({"_id": existing_review["_id"]})
            if review:
                review["id"] = str(review["_id"])
                del review["_id"]
            
            # Update pet average rating
            await update_pet_average_rating(pet_id, database)
            
            return review
        
        # Create new review
        now = datetime.utcnow()
        review_doc = {
            "pet_id": pet_id,
            "reviewer_id": user_id,
            "reviewer_name": user_name,
            "reviewer_avatar": user_avatar,
            "rating": review_data["rating"],
            "comment": review_data["comment"],
            "created_at": now,
            "updated_at": None
        }
        
        result = await database.pet_reviews.insert_one(review_doc)
        
        # Get the created review
        review = await database.pet_reviews.find_one({"_id": result.inserted_id})
        if review:
            review["id"] = str(review["_id"])
            del review["_id"]
        
        # Update pet average rating
        await update_pet_average_rating(pet_id, database)
        
        return review
        
    except Exception as e:
        print(f"Error creating pet review: {str(e)}")
        return None


async def get_pet_reviews(pet_id: str, request: Request, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """Get all reviews for a pet"""
    try:
        database = request.app.mongodb
        
        # Check if pet exists
        pet = await PetModel.get_pet_by_id(pet_id, database)
        if not pet:
            return []
            
        cursor = database.pet_reviews.find({"pet_id": pet_id}).sort("created_at", -1).skip(skip).limit(limit)
        
        reviews = []
        async for review in cursor:
            review["id"] = str(review["_id"])
            del review["_id"]
            reviews.append(review)
            
        return reviews
        
    except Exception as e:
        print(f"Error getting pet reviews: {str(e)}")
        return []


async def update_pet_average_rating(pet_id: str, database) -> None:
    """Update the average rating of a pet"""
    try:
        from bson import ObjectId
        
        pipeline = [
            {"$match": {"pet_id": pet_id}},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ]
        
        result = await database.pet_reviews.aggregate(pipeline).to_list(1)
        
        if result:
            avg_rating = result[0]["avg_rating"]
            count = result[0]["count"]
            
            await database.pets.update_one(
                {"_id": ObjectId(pet_id)},
                {
                    "$set": {
                        "average_rating": avg_rating,
                        "review_count": count
                    }
                }
            )
    except Exception as e:
        print(f"Error updating pet average rating: {str(e)}")
        return None 