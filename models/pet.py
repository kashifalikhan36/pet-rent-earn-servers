from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class PetModel:
    """Pet listing model for MongoDB operations"""
    
    @staticmethod
    async def create_pet(pet_data: Dict[str, Any], database) -> Optional[Dict[str, Any]]:
        """Create a new pet listing"""
        try:
            # Add timestamps
            pet_data["created_at"] = datetime.utcnow()
            pet_data["updated_at"] = datetime.utcnow()
            
            result = await database.pets.insert_one(pet_data)
            
            # Return the created pet
            pet = await database.pets.find_one({"_id": result.inserted_id})
            if pet:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
            return pet
            
        except Exception as e:
            print(f"Error creating pet: {e}")
            return None
    
    @staticmethod
    async def get_pet_by_id(pet_id: str, database) -> Optional[Dict[str, Any]]:
        """Get pet by ID"""
        try:
            pet = await database.pets.find_one({"_id": ObjectId(pet_id)})
            if pet:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
            return pet
        except Exception as e:
            print(f"Error getting pet: {e}")
            return None
    
    @staticmethod
    async def get_pets_by_owner(owner_id: str, database) -> List[Dict[str, Any]]:
        """Get all pets owned by a user"""
        try:
            cursor = database.pets.find({"owner_id": owner_id}).sort("created_at", -1)
            pets = []
            async for pet in cursor:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
                pets.append(pet)
            return pets
        except Exception as e:
            print(f"Error getting pets by owner: {e}")
            return []
    
    @staticmethod
    async def search_pets(filters: Dict[str, Any], database, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Search pets with filters"""
        try:
            query = {"status": "active"}
            
            # Apply filters
            if filters.get("species"):
                query["species"] = {"$regex": filters["species"], "$options": "i"}
            if filters.get("breed"):
                query["breed"] = {"$regex": filters["breed"], "$options": "i"}
            if filters.get("age_min") is not None:
                query["age"] = {"$gte": filters["age_min"]}
            if filters.get("age_max") is not None:
                if "age" in query:
                    query["age"]["$lte"] = filters["age_max"]
                else:
                    query["age"] = {"$lte": filters["age_max"]}
            if filters.get("price_min") is not None:
                query["daily_rate"] = {"$gte": filters["price_min"]}
            if filters.get("price_max") is not None:
                if "daily_rate" in query:
                    query["daily_rate"]["$lte"] = filters["price_max"]
                else:
                    query["daily_rate"] = {"$lte": filters["price_max"]}
            if filters.get("location"):
                # Geospatial search if coordinates provided
                if "coordinates" in filters["location"]:
                    query["location.coordinates"] = {
                        "$near": {
                            "$geometry": {
                                "type": "Point",
                                "coordinates": filters["location"]["coordinates"]
                            },
                            "$maxDistance": filters.get("radius", 10000)  # 10km default
                        }
                    }
                else:
                    query["location.city"] = {"$regex": filters["location"]["city"], "$options": "i"}
            
            cursor = database.pets.find(query).sort("created_at", -1).skip(skip).limit(limit)
            pets = []
            async for pet in cursor:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
                pets.append(pet)
            return pets
        except Exception as e:
            print(f"Error searching pets: {e}")
            return []
    
    @staticmethod
    async def update_pet(pet_id: str, update_data: Dict[str, Any], database) -> Optional[Dict[str, Any]]:
        """Update pet listing"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await database.pets.update_one(
                {"_id": ObjectId(pet_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return await PetModel.get_pet_by_id(pet_id, database)
            return None
        except Exception as e:
            print(f"Error updating pet: {e}")
            return None
    
    @staticmethod
    async def delete_pet(pet_id: str, database) -> bool:
        """Delete pet listing"""
        try:
            result = await database.pets.delete_one({"_id": ObjectId(pet_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting pet: {e}")
            return False
    
    @staticmethod
    async def get_featured_pets(database, limit: int = 10) -> List[Dict[str, Any]]:
        """Get featured pet listings"""
        try:
            cursor = database.pets.find({
                "status": "active",
                "featured": True
            }).sort("created_at", -1).limit(limit)
            
            pets = []
            async for pet in cursor:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
                pets.append(pet)
            return pets
        except Exception as e:
            print(f"Error getting featured pets: {e}")
            return []
    
    @staticmethod
    async def add_to_favorites(user_id: str, pet_id: str, database) -> bool:
        """Add pet to user's favorites"""
        try:
            result = await database.favorites.update_one(
                {"user_id": user_id},
                {
                    "$addToSet": {"pet_ids": pet_id},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding to favorites: {e}")
            return False
    
    @staticmethod
    async def remove_from_favorites(user_id: str, pet_id: str, database) -> bool:
        """Remove pet from user's favorites"""
        try:
            await database.favorites.update_one(
                {"user_id": user_id},
                {
                    "$pull": {"pet_ids": pet_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return True
        except Exception as e:
            print(f"Error removing from favorites: {e}")
            return False
    
    @staticmethod
    async def get_user_favorites(user_id: str, database) -> List[Dict[str, Any]]:
        """Get user's favorite pets"""
        try:
            favorites = await database.favorites.find_one({"user_id": user_id})
            if not favorites or not favorites.get("pet_ids"):
                return []
            
            # Get pet details
            pet_ids = [ObjectId(pet_id) for pet_id in favorites["pet_ids"]]
            cursor = database.pets.find({"_id": {"$in": pet_ids}})
            
            pets = []
            async for pet in cursor:
                pet["id"] = str(pet["_id"])
                del pet["_id"]
                pets.append(pet)
            return pets
        except Exception as e:
            print(f"Error getting user favorites: {e}")
            return []
    
    @staticmethod
    async def increment_view_count(pet_id: str, database) -> bool:
        """Increment pet view count"""
        try:
            await database.pets.update_one(
                {"_id": ObjectId(pet_id)},
                {
                    "$inc": {"view_count": 1},
                    "$set": {"last_viewed_at": datetime.utcnow()}
                }
            )
            return True
        except Exception as e:
            print(f"Error incrementing view count: {e}")
            return False 