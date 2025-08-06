from typing import List, Dict, Any, Optional, Set
from datetime import date, datetime, timedelta
from bson import ObjectId
from fastapi import Request, HTTPException, status

from schemas.calendar import BlockedDateReason


async def create_blocked_date(
    pet_id: str,
    owner_id: str,
    start_date: date,
    end_date: date,
    reason: BlockedDateReason,
    notes: Optional[str] = None,
    request: Request = None
) -> Dict[str, Any]:
    """
    Block dates for a pet
    """
    database = request.app.mongodb
    
    # Check if pet exists and belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(pet_id),
        "owner_id": owner_id
    })
    
    if not pet:
        return None
        
    # Check if there are any bookings in the date range
    conflicting_bookings = await database.bookings.find({
        "pet_id": pet_id,
        "status": {"$in": ["pending", "confirmed"]},
        "$or": [
            {  # Case 1: Booking starts during the block period
                "start_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 2: Booking ends during the block period
                "end_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 3: Booking spans the entire block period
                "$and": [
                    {"start_date": {"$lte": start_date}},
                    {"end_date": {"$gte": end_date}}
                ]
            }
        ]
    }).to_list(length=10)
    
    if conflicting_bookings:
        booking_ids = [str(b["_id"]) for b in conflicting_bookings]
        return {
            "success": False,
            "message": "Cannot block dates with existing bookings",
            "conflicting_bookings": booking_ids
        }
    
    # Check if dates are already blocked
    existing_blocks = await database.blocked_dates.find({
        "pet_id": pet_id,
        "$or": [
            {  # Case 1: Existing block starts during the new block period
                "start_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 2: Existing block ends during the new block period
                "end_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 3: Existing block spans the entire new block period
                "$and": [
                    {"start_date": {"$lte": start_date}},
                    {"end_date": {"$gte": end_date}}
                ]
            }
        ]
    }).to_list(length=10)
    
    if existing_blocks:
        block_ids = [str(b["_id"]) for b in existing_blocks]
        return {
            "success": False,
            "message": "Some dates are already blocked",
            "existing_blocks": block_ids
        }
    
    # Create blocked date
    now = datetime.utcnow()
    blocked_date = {
        "pet_id": pet_id,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
        "notes": notes,
        "created_at": now,
        "updated_at": now
    }
    
    result = await database.blocked_dates.insert_one(blocked_date)
    
    if not result.inserted_id:
        return {
            "success": False,
            "message": "Failed to create blocked date"
        }
        
    blocked_date["id"] = str(result.inserted_id)
    blocked_date["success"] = True
    
    return blocked_date


async def update_blocked_date(
    block_id: str,
    owner_id: str,
    update_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """
    Update a blocked date
    """
    database = request.app.mongodb
    
    # Get the blocked date
    blocked_date = await database.blocked_dates.find_one({
        "_id": ObjectId(block_id)
    })
    
    if not blocked_date:
        return {
            "success": False,
            "message": "Blocked date not found"
        }
    
    # Check if pet belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(blocked_date["pet_id"]),
        "owner_id": owner_id
    })
    
    if not pet:
        return {
            "success": False,
            "message": "You don't have permission to update this blocked date"
        }
    
    # Prepare update data
    update_dict = {}
    
    if "start_date" in update_data:
        update_dict["start_date"] = update_data["start_date"]
    
    if "end_date" in update_data:
        update_dict["end_date"] = update_data["end_date"]
    
    if "reason" in update_data:
        update_dict["reason"] = update_data["reason"]
    
    if "notes" in update_data:
        update_dict["notes"] = update_data["notes"]
    
    # Add updated timestamp
    update_dict["updated_at"] = datetime.utcnow()
    
    if not update_dict or len(update_dict) == 1:  # Only updated_at
        return {
            "success": True,
            "message": "No changes to update"
        }
    
    # Check for date conflicts if dates changed
    if "start_date" in update_dict or "end_date" in update_dict:
        start_date = update_dict.get("start_date", blocked_date["start_date"])
        end_date = update_dict.get("end_date", blocked_date["end_date"])
        
        # Check if there are any bookings in the date range
        conflicting_bookings = await database.bookings.find({
            "pet_id": blocked_date["pet_id"],
            "status": {"$in": ["pending", "confirmed"]},
            "$or": [
                {  # Case 1: Booking starts during the block period
                    "start_date": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                },
                {  # Case 2: Booking ends during the block period
                    "end_date": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                },
                {  # Case 3: Booking spans the entire block period
                    "$and": [
                        {"start_date": {"$lte": start_date}},
                        {"end_date": {"$gte": end_date}}
                    ]
                }
            ]
        }).to_list(length=10)
        
        if conflicting_bookings:
            booking_ids = [str(b["_id"]) for b in conflicting_bookings]
            return {
                "success": False,
                "message": "Cannot block dates with existing bookings",
                "conflicting_bookings": booking_ids
            }
        
        # Check if dates overlap with other blocked dates
        existing_blocks = await database.blocked_dates.find({
            "pet_id": blocked_date["pet_id"],
            "_id": {"$ne": ObjectId(block_id)},
            "$or": [
                {  # Case 1: Existing block starts during the new block period
                    "start_date": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                },
                {  # Case 2: Existing block ends during the new block period
                    "end_date": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                },
                {  # Case 3: Existing block spans the entire new block period
                    "$and": [
                        {"start_date": {"$lte": start_date}},
                        {"end_date": {"$gte": end_date}}
                    ]
                }
            ]
        }).to_list(length=10)
        
        if existing_blocks:
            block_ids = [str(b["_id"]) for b in existing_blocks]
            return {
                "success": False,
                "message": "Some dates overlap with existing blocked dates",
                "existing_blocks": block_ids
            }
    
    # Update blocked date
    result = await database.blocked_dates.update_one(
        {"_id": ObjectId(block_id)},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        return {
            "success": False,
            "message": "Failed to update blocked date"
        }
    
    # Get updated blocked date
    updated_block = await database.blocked_dates.find_one({"_id": ObjectId(block_id)})
    updated_block["id"] = str(updated_block.pop("_id"))
    updated_block["success"] = True
    
    return updated_block


async def delete_blocked_date(
    block_id: str,
    owner_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Delete a blocked date
    """
    database = request.app.mongodb
    
    # Get the blocked date
    blocked_date = await database.blocked_dates.find_one({
        "_id": ObjectId(block_id)
    })
    
    if not blocked_date:
        return {
            "success": False,
            "message": "Blocked date not found"
        }
    
    # Check if pet belongs to owner
    pet = await database.pets.find_one({
        "_id": ObjectId(blocked_date["pet_id"]),
        "owner_id": owner_id
    })
    
    if not pet:
        return {
            "success": False,
            "message": "You don't have permission to delete this blocked date"
        }
    
    # Delete blocked date
    result = await database.blocked_dates.delete_one({"_id": ObjectId(block_id)})
    
    if result.deleted_count == 0:
        return {
            "success": False,
            "message": "Failed to delete blocked date"
        }
    
    return {
        "success": True,
        "message": "Blocked date deleted successfully"
    }


async def get_pet_calendar(
    pet_id: str,
    start_date: date,
    end_date: date,
    request: Request
) -> Dict[str, Any]:
    """
    Get calendar data for a pet in a date range
    """
    database = request.app.mongodb
    
    # Check if pet exists
    pet = await database.pets.find_one({"_id": ObjectId(pet_id)})
    
    if not pet:
        return {
            "success": False,
            "message": "Pet not found"
        }
    
    # Get all dates in range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Create calendar with all dates available by default
    calendar = {d.isoformat(): {"date": d, "status": "available"} for d in date_range}
    
    # Get blocked dates
    blocked_dates = await database.blocked_dates.find({
        "pet_id": pet_id,
        "$or": [
            {"start_date": {"$lte": end_date}},
            {"end_date": {"$gte": start_date}}
        ]
    }).to_list(length=100)
    
    # Mark blocked dates
    for block in blocked_dates:
        block_start = max(block["start_date"], start_date)
        block_end = min(block["end_date"], end_date)
        current_date = block_start
        
        while current_date <= block_end:
            date_key = current_date.isoformat()
            calendar[date_key] = {
                "date": current_date,
                "status": "blocked",
                "reason": block["reason"],
                "block_id": str(block["_id"])
            }
            current_date += timedelta(days=1)
    
    # Get bookings
    bookings = await database.bookings.find({
        "pet_id": pet_id,
        "status": {"$in": ["pending", "confirmed"]},
        "$or": [
            {"start_date": {"$lte": end_date}},
            {"end_date": {"$gte": start_date}}
        ]
    }).to_list(length=100)
    
    # Mark booked dates
    for booking in bookings:
        booking_start = max(booking["start_date"], start_date)
        booking_end = min(booking["end_date"], end_date)
        current_date = booking_start
        
        while current_date <= booking_end:
            date_key = current_date.isoformat()
            calendar[date_key] = {
                "date": current_date,
                "status": "booked",
                "booking_id": str(booking["_id"]),
                "booking_status": booking["status"],
                "renter_id": booking.get("renter_id")
            }
            current_date += timedelta(days=1)
    
    # Convert calendar dict to list
    calendar_list = list(calendar.values())
    
    return {
        "success": True,
        "pet_id": pet_id,
        "pet_name": pet.get("name", ""),
        "start_date": start_date,
        "end_date": end_date,
        "calendar": calendar_list
    }


async def get_user_schedule(
    user_id: str,
    start_date: date,
    end_date: date,
    request: Request,
    as_owner: bool = None
) -> List[Dict[str, Any]]:
    """
    Get user's schedule for the date range (bookings and blocked dates)
    """
    database = request.app.mongodb
    
    events = []
    
    # Get user's pets
    if as_owner is None or as_owner:
        user_pets = await database.pets.find({"owner_id": user_id}).to_list(length=100)
        pet_ids = [str(pet["_id"]) for pet in user_pets]
        pet_dict = {str(pet["_id"]): pet for pet in user_pets}
        
        # Get blocked dates for user's pets
        blocked_dates = await database.blocked_dates.find({
            "pet_id": {"$in": pet_ids},
            "$or": [
                {"start_date": {"$lte": end_date}},
                {"end_date": {"$gte": start_date}}
            ]
        }).to_list(length=100)
        
        # Add blocked dates to events
        for block in blocked_dates:
            pet_id = block["pet_id"]
            pet = pet_dict.get(pet_id)
            
            if pet:
                pet_photo = None
                if "photos" in pet and pet["photos"]:
                    for photo in pet["photos"]:
                        if photo.get("is_primary"):
                            pet_photo = photo.get("url")
                            break
                    # If no primary photo found, use the first one
                    if not pet_photo and pet["photos"]:
                        pet_photo = pet["photos"][0].get("url")
                
                events.append({
                    "id": str(block["_id"]),
                    "pet_id": pet_id,
                    "pet_name": pet.get("name", "Unknown Pet"),
                    "pet_photo": pet_photo,
                    "start_date": block["start_date"],
                    "end_date": block["end_date"],
                    "event_type": "blocked",
                    "status": "blocked",
                    "notes": block.get("notes"),
                    "reason": block.get("reason")
                })
    
    # Get user's bookings as owner
    if as_owner is None or as_owner:
        # First get the bookings where user is the owner (seller)
        owner_bookings_query = {
            "$or": [
                {"start_date": {"$lte": end_date, "$gte": start_date}},
                {"end_date": {"$lte": end_date, "$gte": start_date}},
                {
                    "$and": [
                        {"start_date": {"$lte": start_date}},
                        {"end_date": {"$gte": end_date}}
                    ]
                }
            ]
        }
        
        # Join with pets collection to find owner
        pipeline = [
            {"$match": owner_bookings_query},
            {
                "$lookup": {
                    "from": "pets",
                    "let": {"pet_id": {"$toObjectId": "$pet_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$_id", "$$pet_id"]},
                                        {"$eq": ["$owner_id", user_id]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "pet_info"
                }
            },
            {"$match": {"pet_info": {"$ne": []}}},
            {
                "$lookup": {
                    "from": "users",
                    "let": {"renter_id": "$renter_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$_id", {"$toObjectId": "$$renter_id"}]}
                            }
                        }
                    ],
                    "as": "renter_info"
                }
            }
        ]
        
        owner_bookings = await database.bookings.aggregate(pipeline).to_list(length=100)
        
        # Add owner bookings to events
        for booking in owner_bookings:
            pet_info = booking["pet_info"][0] if booking["pet_info"] else {}
            renter_info = booking["renter_info"][0] if booking["renter_info"] else {}
            
            pet_photo = None
            if "photos" in pet_info and pet_info["photos"]:
                for photo in pet_info["photos"]:
                    if photo.get("is_primary"):
                        pet_photo = photo.get("url")
                        break
                # If no primary photo found, use the first one
                if not pet_photo and pet_info["photos"]:
                    pet_photo = pet_info["photos"][0].get("url")
            
            events.append({
                "id": str(booking["_id"]),
                "pet_id": booking["pet_id"],
                "pet_name": pet_info.get("name", "Unknown Pet"),
                "pet_photo": pet_photo,
                "start_date": booking["start_date"],
                "end_date": booking["end_date"],
                "event_type": "booking",
                "status": booking["status"],
                "with_user_id": booking["renter_id"],
                "with_user_name": renter_info.get("name", "Unknown User"),
                "price": booking.get("total_price"),
                "notes": f"Booking as owner - {booking['status']}"
            })
    
    # Get user's bookings as renter
    if as_owner is None or not as_owner:
        renter_bookings = await database.bookings.find({
            "renter_id": user_id,
            "$or": [
                {"start_date": {"$lte": end_date, "$gte": start_date}},
                {"end_date": {"$lte": end_date, "$gte": start_date}},
                {
                    "$and": [
                        {"start_date": {"$lte": start_date}},
                        {"end_date": {"$gte": end_date}}
                    ]
                }
            ]
        }).to_list(length=100)
        
        # Get pet and owner details
        for booking in renter_bookings:
            pet = await database.pets.find_one({"_id": ObjectId(booking["pet_id"])})
            if pet:
                owner = await database.users.find_one({"_id": ObjectId(pet["owner_id"])})
                
                pet_photo = None
                if "photos" in pet and pet["photos"]:
                    for photo in pet["photos"]:
                        if photo.get("is_primary"):
                            pet_photo = photo.get("url")
                            break
                    # If no primary photo found, use the first one
                    if not pet_photo and pet["photos"]:
                        pet_photo = pet["photos"][0].get("url")
                
                events.append({
                    "id": str(booking["_id"]),
                    "pet_id": booking["pet_id"],
                    "pet_name": pet.get("name", "Unknown Pet"),
                    "pet_photo": pet_photo,
                    "start_date": booking["start_date"],
                    "end_date": booking["end_date"],
                    "event_type": "booking",
                    "status": booking["status"],
                    "with_user_id": pet["owner_id"],
                    "with_user_name": owner.get("name", "Unknown Owner") if owner else "Unknown Owner",
                    "price": booking.get("total_price"),
                    "notes": f"Booking as renter - {booking['status']}"
                })
    
    # Sort events by start date
    events.sort(key=lambda e: e["start_date"])
    
    return events


async def check_date_availability(
    pet_id: str,
    start_date: date,
    end_date: date,
    request: Request
) -> Dict[str, Any]:
    """
    Check if dates are available for booking
    """
    database = request.app.mongodb
    
    # Check if pet exists
    pet = await database.pets.find_one({"_id": ObjectId(pet_id)})
    
    if not pet:
        return {
            "is_available": False,
            "blocked_reason": "Pet not found"
        }
    
    # Check pet availability period
    if pet.get("availableFrom") and start_date < pet["availableFrom"].date():
        return {
            "is_available": False,
            "blocked_reason": f"Pet is only available from {pet['availableFrom'].date().isoformat()}"
        }
    
    if pet.get("availableTo") and end_date > pet["availableTo"].date():
        return {
            "is_available": False,
            "blocked_reason": f"Pet is only available until {pet['availableTo'].date().isoformat()}"
        }
    
    # Check if there are any bookings in the date range
    conflicting_bookings = await database.bookings.find({
        "pet_id": pet_id,
        "status": {"$in": ["pending", "confirmed"]},
        "$or": [
            {  # Case 1: Existing booking starts during the new booking period
                "start_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 2: Existing booking ends during the new booking period
                "end_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 3: Existing booking spans the entire new booking period
                "$and": [
                    {"start_date": {"$lte": start_date}},
                    {"end_date": {"$gte": end_date}}
                ]
            }
        ]
    }).to_list(length=10)
    
    if conflicting_bookings:
        booking_ids = [str(b["_id"]) for b in conflicting_bookings]
        
        # Determine conflicting dates
        conflicting_dates = set()
        for booking in conflicting_bookings:
            booking_start = booking["start_date"]
            booking_end = booking["end_date"]
            current_date = max(booking_start, start_date)
            while current_date <= min(booking_end, end_date):
                conflicting_dates.add(current_date)
                current_date += timedelta(days=1)
        
        return {
            "is_available": False,
            "blocked_reason": "Some dates are already booked",
            "booking_ids": booking_ids,
            "conflicting_dates": sorted(list(conflicting_dates))
        }
    
    # Check if dates are blocked
    blocked_dates = await database.blocked_dates.find({
        "pet_id": pet_id,
        "$or": [
            {  # Case 1: Blocked period starts during the new booking period
                "start_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 2: Blocked period ends during the new booking period
                "end_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            {  # Case 3: Blocked period spans the entire new booking period
                "$and": [
                    {"start_date": {"$lte": start_date}},
                    {"end_date": {"$gte": end_date}}
                ]
            }
        ]
    }).to_list(length=10)
    
    if blocked_dates:
        # Determine conflicting dates
        conflicting_dates = set()
        for block in blocked_dates:
            block_start = block["start_date"]
            block_end = block["end_date"]
            current_date = max(block_start, start_date)
            while current_date <= min(block_end, end_date):
                conflicting_dates.add(current_date)
                current_date += timedelta(days=1)
        
        return {
            "is_available": False,
            "blocked_reason": f"Some dates are blocked: {block.get('reason', 'unavailable')}",
            "conflicting_dates": sorted(list(conflicting_dates))
        }
    
    # All dates are available
    return {
        "is_available": True
    } 