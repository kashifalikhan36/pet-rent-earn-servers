from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from fastapi import Request, HTTPException, status

from schemas.health_record import RecordType


async def create_health_record(
    pet_id: str,
    owner_id: str,
    record_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """
    Create a new health record for a pet
    """
    database = request.app.mongodb
    
    # Check if pet exists and belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(pet_id),
        "owner_id": owner_id
    })
    
    if not pet:
        return None
    
    # Create health record
    now = datetime.utcnow()
    health_record = {
        "pet_id": pet_id,
        "title": record_data["title"],
        "record_type": record_data["record_type"],
        "date": record_data["date"],
        "description": record_data["description"],
        "provider_name": record_data.get("provider_name"),
        "provider_contact": record_data.get("provider_contact"),
        "notes": record_data.get("notes"),
        "attachments": record_data.get("attachments", []),
        "reminder_date": record_data.get("reminder_date"),
        "metadata": record_data.get("metadata", {}),
        "created_at": now,
        "updated_at": now,
        "created_by": owner_id
    }
    
    result = await database.health_records.insert_one(health_record)
    
    if not result.inserted_id:
        return None
    
    # Add pet name to response
    health_record["id"] = str(result.inserted_id)
    health_record["pet_name"] = pet.get("name")
    
    # Create reminder if reminder_date is provided
    if record_data.get("reminder_date"):
        try:
            from crud.notification import create_notification
            from schemas.notification import NotificationType
            
            reminder_date = record_data["reminder_date"]
            
            await database.reminders.insert_one({
                "user_id": owner_id,
                "pet_id": pet_id,
                "health_record_id": str(result.inserted_id),
                "title": f"Health Reminder: {record_data['title']}",
                "description": f"Reminder for {pet.get('name')}: {record_data['title']}",
                "reminder_date": reminder_date,
                "created_at": now
            })
            
        except Exception as e:
            # Log error but don't fail the record creation
            print(f"Failed to create reminder: {str(e)}")
    
    return health_record


async def update_health_record(
    record_id: str,
    owner_id: str,
    record_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """
    Update a health record
    """
    database = request.app.mongodb
    
    # Get the health record
    record = await database.health_records.find_one({
        "_id": ObjectId(record_id)
    })
    
    if not record:
        return None
    
    # Check if pet belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(record["pet_id"]),
        "owner_id": owner_id
    })
    
    if not pet:
        return None
    
    # Prepare update data
    update_data = {}
    
    for field in [
        "title", "record_type", "date", "description", "provider_name",
        "provider_contact", "notes", "attachments", "reminder_date", "metadata"
    ]:
        if field in record_data:
            update_data[field] = record_data[field]
    
    if not update_data:
        # No fields to update
        return await get_health_record(record_id, request)
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update health record
    result = await database.health_records.update_one(
        {"_id": ObjectId(record_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and not result.matched_count:
        return None
    
    # Update reminder if reminder_date is changed
    if "reminder_date" in update_data:
        # Delete existing reminder
        await database.reminders.delete_many({
            "health_record_id": record_id
        })
        
        # Create new reminder if date is provided
        if update_data["reminder_date"]:
            await database.reminders.insert_one({
                "user_id": owner_id,
                "pet_id": record["pet_id"],
                "health_record_id": record_id,
                "title": f"Health Reminder: {update_data.get('title', record['title'])}",
                "description": f"Reminder for {pet.get('name')}: {update_data.get('title', record['title'])}",
                "reminder_date": update_data["reminder_date"],
                "created_at": datetime.utcnow()
            })
    
    # Return updated health record
    return await get_health_record(record_id, request)


async def delete_health_record(
    record_id: str,
    owner_id: str,
    request: Request
) -> bool:
    """
    Delete a health record
    """
    database = request.app.mongodb
    
    # Get the health record
    record = await database.health_records.find_one({
        "_id": ObjectId(record_id)
    })
    
    if not record:
        return False
    
    # Check if pet belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(record["pet_id"]),
        "owner_id": owner_id
    })
    
    if not pet:
        return False
    
    # Delete health record
    result = await database.health_records.delete_one({
        "_id": ObjectId(record_id)
    })
    
    # Delete related reminders
    await database.reminders.delete_many({
        "health_record_id": record_id
    })
    
    return result.deleted_count > 0


async def get_health_record(
    record_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Get a health record by ID
    """
    database = request.app.mongodb
    
    # Get health record
    record = await database.health_records.find_one({
        "_id": ObjectId(record_id)
    })
    
    if not record:
        return None
    
    # Get pet name
    pet = await database.pets.find_one({
        "_id": ObjectId(record["pet_id"])
    })
    
    if pet:
        record["pet_name"] = pet.get("name")
    
    # Convert ObjectId to string
    record["id"] = str(record.pop("_id"))
    
    return record


async def get_pet_health_records(
    pet_id: str,
    record_type: Optional[RecordType] = None,
    skip: int = 0,
    limit: int = 20,
    request: Request = None
) -> List[Dict[str, Any]]:
    """
    Get all health records for a pet
    """
    database = request.app.mongodb
    
    # Build query
    query = {"pet_id": pet_id}
    
    if record_type:
        query["record_type"] = record_type
    
    # Get records
    cursor = database.health_records.find(query)
    
    # Sort by date in descending order (newest first)
    cursor = cursor.sort("date", -1)
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(limit)
    
    # Convert to list
    records = []
    async for record in cursor:
        record["id"] = str(record.pop("_id"))
        records.append(record)
    
    # Get pet name
    pet = await database.pets.find_one({"_id": ObjectId(pet_id)})
    if pet:
        pet_name = pet.get("name")
        for record in records:
            record["pet_name"] = pet_name
    
    return records


async def check_health_record_access(
    record_id: str,
    user_id: str,
    request: Request
) -> bool:
    """
    Check if user has access to health record
    Owner always has access
    Renters have access if they have an active booking and owner has given permission
    """
    database = request.app.mongodb
    
    # Get the health record
    record = await database.health_records.find_one({
        "_id": ObjectId(record_id)
    })
    
    if not record:
        return False
    
    # Get the pet
    pet = await database.pets.find_one({
        "_id": ObjectId(record["pet_id"])
    })
    
    if not pet:
        return False
    
    # If user is the owner, always allow access
    if pet.get("owner_id") == user_id:
        return True
    
    # Check if user has an active booking for this pet
    active_booking = await database.bookings.find_one({
        "pet_id": record["pet_id"],
        "renter_id": user_id,
        "status": "confirmed",
        "end_date": {"$gte": datetime.utcnow().date()}
    })
    
    # Check if owner allows health records access to renters
    # This could be a setting in the pet document
    allows_health_access = pet.get("share_health_records_with_renters", False)
    
    return active_booking is not None and allows_health_access


async def get_recent_or_upcoming_health_records(
    owner_id: str,
    request: Request,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get recent health records and upcoming reminders for owner's pets
    """
    database = request.app.mongodb
    
    # Get owner's pets
    pets = await database.pets.find({"owner_id": owner_id}).to_list(length=100)
    pet_ids = [str(pet["_id"]) for pet in pets]
    pet_dict = {str(pet["_id"]): pet.get("name", "Unknown Pet") for pet in pets}
    
    today = datetime.utcnow().date()
    
    # Get recent health records (last 30 days)
    recent_records = await database.health_records.find({
        "pet_id": {"$in": pet_ids},
        "date": {"$gte": today.replace(day=today.day-30)}
    }).sort("date", -1).limit(limit).to_list(length=limit)
    
    # Format recent records
    for record in recent_records:
        record["id"] = str(record.pop("_id"))
        record["pet_name"] = pet_dict.get(record["pet_id"], "Unknown Pet")
        record["record_type"] = "recent"
    
    # Get upcoming reminders
    upcoming_reminders = await database.reminders.find({
        "user_id": owner_id,
        "reminder_date": {"$gte": today}
    }).sort("reminder_date", 1).limit(limit).to_list(length=limit)
    
    # Format upcoming reminders
    reminder_records = []
    for reminder in upcoming_reminders:
        reminder["id"] = str(reminder.pop("_id"))
        reminder["pet_name"] = pet_dict.get(reminder["pet_id"], "Unknown Pet")
        reminder["record_type"] = "reminder"
        # If associated with health record, get more info
        if reminder.get("health_record_id"):
            health_record = await database.health_records.find_one({
                "_id": ObjectId(reminder["health_record_id"])
            })
            if health_record:
                reminder["health_record"] = {
                    "id": str(health_record["_id"]),
                    "title": health_record["title"],
                    "record_type": health_record["record_type"]
                }
        reminder_records.append(reminder)
    
    # Combine and sort by date
    all_records = recent_records + reminder_records
    all_records.sort(key=lambda x: x.get("date", x.get("reminder_date", today)), reverse=True)
    
    # Limit to requested number
    return all_records[:limit]


async def upload_health_record_attachment(
    file_url: str,
    record_id: str,
    owner_id: str,
    request: Request
) -> bool:
    """
    Add an attachment URL to a health record
    """
    database = request.app.mongodb
    
    # Get the health record
    record = await database.health_records.find_one({
        "_id": ObjectId(record_id)
    })
    
    if not record:
        return False
    
    # Check if pet belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(record["pet_id"]),
        "owner_id": owner_id
    })
    
    if not pet:
        return False
    
    # Add attachment to health record
    result = await database.health_records.update_one(
        {"_id": ObjectId(record_id)},
        {
            "$push": {"attachments": file_url},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return result.modified_count > 0 