from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from fastapi import Request
from schemas.booking import BookingCreate, BookingStatus, PaymentStatus
from bson.objectid import ObjectId


async def create_booking(
    booking_data: BookingCreate, 
    renter_id: str, 
    request: Request
) -> Optional[Dict[str, Any]]:
    """Create a new booking request."""
    try:
        database = request.app.mongodb
        
        # Get pet details
        pet = await database.pets.find_one({"_id": ObjectId(booking_data.pet_id)})
        if not pet:
            return None
            
        # Check if pet is available
        availability = await check_pet_availability(
            pet["_id"], 
            booking_data.start_date, 
            booking_data.end_date, 
            database
        )
        if not availability["available"]:
            return None
            
        # Calculate booking details
        start_date = booking_data.start_date
        end_date = booking_data.end_date
        total_days = (end_date - start_date).days + 1
        
        daily_rate = pet.get("dailyRate", 0)
        if not daily_rate and pet.get("listingType") == "rent":
            return None
            
        total_amount = daily_rate * total_days
        service_fee = total_amount * 0.10  # 10% service fee
        grand_total = total_amount + service_fee
        
        # Create booking document
        booking_doc = {
            "pet_id": booking_data.pet_id,
            "owner_id": pet["owner_id"],
            "renter_id": renter_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "daily_rate": daily_rate,
            "total_amount": total_amount,
            "service_fee": service_fee,
            "grand_total": grand_total,
            "status": BookingStatus.PENDING,
            "payment_status": PaymentStatus.PENDING,
            "message": booking_data.message,
            "pickup_time": booking_data.pickup_time,
            "dropoff_time": booking_data.dropoff_time,
            "special_requests": booking_data.special_requests,
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        
        # Insert booking
        result = await database.bookings.insert_one(booking_doc)
        
        # Get created booking
        booking = await database.bookings.find_one({"_id": result.inserted_id})
        if booking:
            booking["id"] = str(booking["_id"])
            del booking["_id"]
            
            # Add pet details for convenience
            pet["id"] = str(pet["_id"])
            del pet["_id"]
            booking["pet"] = pet
            
            # Get owner details
            owner = await database.users.find_one({"_id": ObjectId(pet["owner_id"])})
            if owner:
                owner["id"] = str(owner["_id"])
                del owner["_id"]
                booking["owner"] = {
                    "id": owner["id"],
                    "name": owner["name"],
                    "avatar_url": owner.get("avatar_url")
                }
                
            # Get renter details
            renter = await database.users.find_one({"_id": ObjectId(renter_id)})
            if renter:
                renter["id"] = str(renter["_id"])
                del renter["_id"]
                booking["renter"] = {
                    "id": renter["id"],
                    "name": renter["name"],
                    "avatar_url": renter.get("avatar_url")
                }
                
        return booking
        
    except Exception as e:
        print(f"Error creating booking: {e}")
        return None


async def get_booking(booking_id: str, user_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Get booking by ID (only if user is owner or renter)."""
    try:
        database = request.app.mongodb
        
        booking = await database.bookings.find_one({
            "_id": ObjectId(booking_id),
            "$or": [
                {"owner_id": user_id},
                {"renter_id": user_id}
            ]
        })
        
        if booking:
            booking["id"] = str(booking["_id"])
            del booking["_id"]
            
            # Add pet details
            pet = await database.pets.find_one({"_id": ObjectId(booking["pet_id"])})
            if pet:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
                booking["pet"] = pet
                
            # Add owner details
            owner = await database.users.find_one({"_id": ObjectId(booking["owner_id"])})
            if owner:
                owner["id"] = str(owner["_id"])
                del owner["_id"]
                booking["owner"] = {
                    "id": owner["id"],
                    "name": owner["name"],
                    "avatar_url": owner.get("avatar_url")
                }
                
            # Add renter details
            renter = await database.users.find_one({"_id": ObjectId(booking["renter_id"])})
            if renter:
                renter["id"] = str(renter["_id"])
                del renter["_id"]
                booking["renter"] = {
                    "id": renter["id"],
                    "name": renter["name"],
                    "avatar_url": renter.get("avatar_url")
                }
                
        return booking
        
    except Exception as e:
        print(f"Error getting booking: {e}")
        return None


async def check_pet_availability(
    pet_id: str, 
    start_date: date, 
    end_date: date,
    database
) -> Dict[str, Any]:
    """Check if a pet is available for booking in the given date range."""
    try:
        # Convert string pet_id to ObjectId if needed
        if isinstance(pet_id, str):
            pet_id = ObjectId(pet_id)
            
        # Check if pet exists and is active
        pet = await database.pets.find_one({"_id": pet_id})
        if not pet or pet.get("status") != "active" or pet.get("listingType") != "rent":
            return {
                "available": False,
                "reason": "Pet is not available for rent"
            }
            
        # Check if dates are within pet's available range
        pet_available_from = pet.get("availableFrom")
        pet_available_to = pet.get("availableTo")
        
        if pet_available_from and pet_available_from.date() > start_date:
            return {
                "available": False,
                "reason": "Start date is before pet's available from date"
            }
            
        if pet_available_to and pet_available_to.date() < end_date:
            return {
                "available": False,
                "reason": "End date is after pet's available to date"
            }
            
        # Check for existing bookings
        conflicting_bookings = []
        
        # Find bookings that overlap with the requested date range
        async for booking in database.bookings.find({
            "pet_id": str(pet_id),
            "status": {"$in": ["pending", "accepted", "in_progress"]},
            "$or": [
                {"start_date": {"$lte": end_date}, "end_date": {"$gte": start_date}},
                {"start_date": {"$gte": start_date, "$lte": end_date}},
                {"end_date": {"$gte": start_date, "$lte": end_date}}
            ]
        }):
            booking["id"] = str(booking["_id"])
            del booking["_id"]
            conflicting_bookings.append(booking)
            
        if conflicting_bookings:
            return {
                "available": False,
                "reason": "Pet is already booked during these dates",
                "conflicting_bookings": conflicting_bookings
            }
            
        # Find available dates
        available_dates = []
        
        # Create a list of dates from start_date to end_date
        current_date = start_date
        while current_date <= end_date:
            available_dates.append(current_date)
            current_date += timedelta(days=1)
            
        return {
            "available": True,
            "available_dates": available_dates
        }
        
    except Exception as e:
        print(f"Error checking pet availability: {e}")
        return {
            "available": False,
            "reason": "Error checking availability"
        }


async def update_booking_status(
    booking_id: str,
    status: BookingStatus,
    user_id: str,
    request: Request
) -> Optional[Dict[str, Any]]:
    """Update booking status (only if user is owner or renter depending on status)."""
    try:
        database = request.app.mongodb
        
        # Get existing booking
        booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})
        if not booking:
            return None
            
        # Check permissions based on status
        if status == BookingStatus.ACCEPTED or status == BookingStatus.REJECTED:
            # Only owner can accept/reject
            if booking["owner_id"] != user_id:
                return None
        elif status == BookingStatus.CANCELLED:
            # Either owner or renter can cancel
            if booking["owner_id"] != user_id and booking["renter_id"] != user_id:
                return None
        elif status == BookingStatus.COMPLETED:
            # Only owner can mark as completed
            if booking["owner_id"] != user_id:
                return None
                
        # Update booking status
        now = datetime.utcnow()
        result = await database.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": now
                }
            }
        )
        
        if result.modified_count > 0:
            return await get_booking(booking_id, user_id, request)
        return None
        
    except Exception as e:
        print(f"Error updating booking status: {e}")
        return None


async def get_user_bookings(
    user_id: str,
    request: Request,
    as_owner: bool = None,
    status: str = None,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Dict[str, Any]], int]:
    """Get user's bookings with filters."""
    try:
        database = request.app.mongodb
        skip = (page - 1) * limit
        
        # Build query
        query = {}
        if as_owner is not None:
            if as_owner:
                query["owner_id"] = user_id
            else:
                query["renter_id"] = user_id
        else:
            query["$or"] = [{"owner_id": user_id}, {"renter_id": user_id}]
            
        if status:
            query["status"] = status
            
        # Count total matching bookings
        total = await database.bookings.count_documents(query)
        
        # Get bookings with pagination
        bookings = []
        async for booking in database.bookings.find(query).sort("created_at", -1).skip(skip).limit(limit):
            booking["id"] = str(booking["_id"])
            del booking["_id"]
            
            # Get pet basic info
            pet = await database.pets.find_one({"_id": ObjectId(booking["pet_id"])})
            if pet:
                booking["pet_name"] = pet["name"]
                
                # Get primary photo if any
                primary_photo = next((p for p in pet.get("photos", []) if p.get("is_primary")), None)
                if primary_photo:
                    booking["pet_image_url"] = primary_photo.get("url")
                    
            # Get owner name
            owner = await database.users.find_one({"_id": ObjectId(booking["owner_id"])})
            if owner:
                booking["owner_name"] = owner["name"]
                
            # Get renter name
            renter = await database.users.find_one({"_id": ObjectId(booking["renter_id"])})
            if renter:
                booking["renter_name"] = renter["name"]
                
            bookings.append(booking)
            
        return bookings, total
        
    except Exception as e:
        print(f"Error getting user bookings: {e}")
        return [], 0 