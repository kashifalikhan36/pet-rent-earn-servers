from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from fastapi import Request, HTTPException, status


async def create_care_instructions(
    pet_id: str,
    owner_id: str,
    instructions_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """
    Create care instructions for a pet
    """
    database = request.app.mongodb
    
    # Check if pet exists and belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(pet_id),
        "owner_id": owner_id
    })
    
    if not pet:
        return None
    
    # Check if care instructions already exist
    existing = await database.care_instructions.find_one({
        "pet_id": pet_id
    })
    
    if existing:
        return {
            "error": "Care instructions already exist for this pet",
            "instructions_id": str(existing["_id"])
        }
    
    # Create care instructions
    now = datetime.utcnow()
    care_instructions = {
        "pet_id": pet_id,
        "general_notes": instructions_data.get("general_notes"),
        "emergency_contact": instructions_data.get("emergency_contact"),
        "vet_info": instructions_data.get("vet_info"),
        "food_instructions": instructions_data.get("food_instructions"),
        "medication_instructions": instructions_data.get("medication_instructions"),
        "exercise_instructions": instructions_data.get("exercise_instructions"),
        "grooming_instructions": instructions_data.get("grooming_instructions"),
        "behavior_notes": instructions_data.get("behavior_notes"),
        "additional_instructions": instructions_data.get("additional_instructions", []),
        "created_at": now,
        "updated_at": now
    }
    
    result = await database.care_instructions.insert_one(care_instructions)
    
    if not result.inserted_id:
        return None
    
    # Add pet details to the response
    care_instructions["id"] = str(result.inserted_id)
    care_instructions["pet_name"] = pet.get("name")
    
    # Add pet photo if available
    pet_photo = None
    if "photos" in pet and pet["photos"]:
        for photo in pet["photos"]:
            if photo.get("is_primary"):
                pet_photo = photo.get("url")
                break
        # If no primary photo found, use the first one
        if not pet_photo and pet["photos"]:
            pet_photo = pet["photos"][0].get("url")
    
    care_instructions["pet_photo"] = pet_photo
    
    return care_instructions


async def update_care_instructions(
    pet_id: str,
    owner_id: str,
    instructions_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """
    Update care instructions for a pet
    """
    database = request.app.mongodb
    
    # Check if pet exists and belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(pet_id),
        "owner_id": owner_id
    })
    
    if not pet:
        return None
    
    # Check if care instructions exist
    existing = await database.care_instructions.find_one({
        "pet_id": pet_id
    })
    
    if not existing:
        return {
            "error": "Care instructions do not exist for this pet"
        }
    
    # Prepare update data
    update_data = {}
    
    for field in [
        "general_notes", "emergency_contact", "vet_info",
        "food_instructions", "medication_instructions", 
        "exercise_instructions", "grooming_instructions",
        "behavior_notes", "additional_instructions"
    ]:
        if field in instructions_data:
            update_data[field] = instructions_data[field]
    
    if not update_data:
        # No fields to update
        return await get_care_instructions(pet_id, request)
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update care instructions
    result = await database.care_instructions.update_one(
        {"pet_id": pet_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        return None
    
    # Return updated care instructions
    return await get_care_instructions(pet_id, request)


async def delete_care_instructions(
    pet_id: str,
    owner_id: str,
    request: Request
) -> bool:
    """
    Delete care instructions for a pet
    """
    database = request.app.mongodb
    
    # Check if pet exists and belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(pet_id),
        "owner_id": owner_id
    })
    
    if not pet:
        return False
    
    # Delete care instructions
    result = await database.care_instructions.delete_one({
        "pet_id": pet_id
    })
    
    return result.deleted_count > 0


async def get_care_instructions(
    pet_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Get care instructions for a pet
    """
    database = request.app.mongodb
    
    # Get care instructions
    care_instructions = await database.care_instructions.find_one({
        "pet_id": pet_id
    })
    
    if not care_instructions:
        return None
    
    # Get pet details to add to response
    pet = await database.pets.find_one({"_id": ObjectId(pet_id)})
    
    if pet:
        care_instructions["pet_name"] = pet.get("name")
        
        # Add pet photo if available
        pet_photo = None
        if "photos" in pet and pet["photos"]:
            for photo in pet["photos"]:
                if photo.get("is_primary"):
                    pet_photo = photo.get("url")
                    break
            # If no primary photo found, use the first one
            if not pet_photo and pet["photos"]:
                pet_photo = pet["photos"][0].get("url")
        
        care_instructions["pet_photo"] = pet_photo
    
    # Convert ObjectId to string
    care_instructions["id"] = str(care_instructions.pop("_id"))
    
    return care_instructions


async def check_care_instructions_access(
    pet_id: str,
    user_id: str,
    request: Request
) -> bool:
    """
    Check if user has access to care instructions
    Owner always has access
    Renters have access if they have an active booking
    """
    database = request.app.mongodb
    
    # Check if user is the owner
    pet = await database.pets.find_one({
        "_id": ObjectId(pet_id)
    })
    
    if not pet:
        return False
    
    # If user is the owner, always allow access
    if pet.get("owner_id") == user_id:
        return True
    
    # Check if user has an active booking for this pet
    active_booking = await database.bookings.find_one({
        "pet_id": pet_id,
        "renter_id": user_id,
        "status": "confirmed",
        "end_date": {"$gte": datetime.utcnow().date()}
    })
    
    return active_booking is not None 