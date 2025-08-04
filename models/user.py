from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, EmailStr, validator
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings
import secrets
import urllib.parse

settings = get_settings()

# Create MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URI)
# Extract database name from URI, fallback to 'petrent' if not specified
parsed_uri = urllib.parse.urlparse(settings.MONGODB_URI)
db_name = parsed_uri.path.lstrip('/') if parsed_uri.path and parsed_uri.path != '/' else 'petrent'
db = client[db_name]
users_collection = db.users


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserModel:
    @staticmethod
    async def create(name: str, email: str, password_hash: str = None, role: str = "user", 
                    google_id: str = None, profile_picture: str = None) -> dict:
        """Create a new user in the database"""
        user = {
            "name": name,
            "email": email.lower(),
            "role": role,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        # Add password hash only if provided (for regular users)
        if password_hash:
            user["password_hash"] = password_hash
            
        # Add Google OAuth fields if provided
        if google_id:
            user["google_id"] = google_id
            user["oauth_provider"] = "google"
            
        if profile_picture:
            user["profile_picture"] = profile_picture
            
        result = await users_collection.insert_one(user)
        user["id"] = str(result.inserted_id)
        return user

    @staticmethod
    async def get_by_email(email: str) -> Optional[dict]:
        """Get a user by email address"""
        user = await users_collection.find_one({"email": email.lower()})
        if user:
            user["id"] = str(user.pop("_id"))
        return user

    @staticmethod
    async def get_by_id(user_id: str) -> Optional[dict]:
        """Get a user by ID"""
        if not ObjectId.is_valid(user_id):
            return None
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["id"] = str(user.pop("_id"))
        return user
    
    @staticmethod
    async def get_by_google_id(google_id: str) -> Optional[dict]:
        """Get a user by Google ID"""
        user = await users_collection.find_one({"google_id": google_id})
        if user:
            user["id"] = str(user.pop("_id"))
        return user
        
    @staticmethod
    async def update(user_id: str, update_data: dict) -> Optional[dict]:
        """Update a user's information"""
        if not ObjectId.is_valid(user_id):
            return None
        
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.modified_count:
            return await UserModel.get_by_id(user_id)
        return None

    @staticmethod
    async def list(skip: int = 0, limit: int = 20) -> tuple:
        """Get a list of users with pagination"""
        users = []
        cursor = users_collection.find().sort("created_at", -1).skip(skip).limit(limit)
        async for user in cursor:
            user["id"] = str(user.pop("_id"))
            # Don't send password hash to client
            user.pop("password_hash", None)
            users.append(user)
        
        total = await users_collection.count_documents({})
        return users, total

    @staticmethod
    async def delete(user_id: str) -> bool:
        """Delete a user by ID"""
        if not ObjectId.is_valid(user_id):
            return False
        
        result = await users_collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    @staticmethod
    async def update_last_active(user_id: str) -> bool:
        """Update user's last active timestamp"""
        if not ObjectId.is_valid(user_id):
            return False
        
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_active": datetime.utcnow()}}
        )
        return True

    @staticmethod
    async def get_user_stats() -> Dict[str, Any]:
        """Get overall user statistics"""
        now = datetime.utcnow()
        
        # Get total users
        total_users = await users_collection.count_documents({})
        
        # Get admin users
        admin_users = await users_collection.count_documents({"role": "admin"})
        
        # Get active users in different time periods
        last_24h = now - timedelta(days=1)
        active_users_24h = await users_collection.count_documents({
            "last_active": {"$gte": last_24h}
        })
        
        last_7d = now - timedelta(days=7)
        active_users_7d = await users_collection.count_documents({
            "last_active": {"$gte": last_7d}
        })
        
        last_30d = now - timedelta(days=30)
        active_users_30d = await users_collection.count_documents({
            "last_active": {"$gte": last_30d}
        })
        
        # Get new signups
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        new_signups_today = await users_collection.count_documents({
            "created_at": {"$gte": today_start}
        })
        
        week_ago = now - timedelta(days=7)
        new_signups_7d = await users_collection.count_documents({
            "created_at": {"$gte": week_ago}
        })
        
        # Get daily user growth for the last 30 days
        thirty_days_ago = now - timedelta(days=30)
        
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": thirty_days_ago}
                }
            },
            {
                "$project": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "new": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        daily_growth = []
        running_total = await users_collection.count_documents({
            "created_at": {"$lt": thirty_days_ago}
        })
        
        cursor = await users_collection.aggregate(pipeline).to_list(30)
        
        # Fill in missing dates with zeros
        date_dict = {item["_id"]: item["new"] for item in cursor}
        
        current_date = thirty_days_ago
        while current_date <= now:
            date_str = current_date.strftime("%Y-%m-%d")
            new_users = date_dict.get(date_str, 0)
            running_total += new_users
            
            daily_growth.append({
                "date": date_str,
                "total": running_total,
                "new": new_users
            })
            
            current_date += timedelta(days=1)
        
        return {
            "total_users": total_users,
            "active_users_last_24h": active_users_24h,
            "active_users_last_7d": active_users_7d,
            "active_users_last_30d": active_users_30d,
            "admin_users": admin_users,
            "new_signups_today": new_signups_today,
            "new_signups_last_7d": new_signups_7d,
            "user_growth": daily_growth
        }

    @staticmethod
    async def search_users(
        query: Optional[str] = None,
        role: Optional[str] = None,
        min_conversions: Optional[int] = None,
        max_conversions: Optional[int] = None,
        signup_after: Optional[datetime] = None,
        signup_before: Optional[datetime] = None,
        last_active_after: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_dir: int = -1,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Advanced user search with filters"""
        # Build filter
        filter_query = {}
        
        if query:
            filter_query["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}}
            ]
        
        if role:
            filter_query["role"] = role
            
        date_filter = {}
        if signup_after:
            date_filter["$gte"] = signup_after
        if signup_before:
            date_filter["$lte"] = signup_before
        if date_filter:
            filter_query["created_at"] = date_filter
            
        if last_active_after:
            filter_query["last_active"] = {"$gte": last_active_after}
        
        # Execute query
        users = []
        
        # Map sort fields to MongoDB fields
        sort_field_map = {
            "name": "name",
            "email": "email",
            "created_at": "created_at",
            "last_active": "last_active",
        }
        
        mongodb_sort_field = sort_field_map.get(sort_by, "created_at")
        
        cursor = users_collection.find(filter_query).sort(
            mongodb_sort_field, sort_dir
        ).skip(skip).limit(limit)
        
        async for user in cursor:
            user_id = user["_id"]
            user["id"] = str(user_id)
            user.pop("password_hash", None)
            user.pop("_id", None)
            users.append(user)
        
        total_count = await users_collection.count_documents(filter_query)
        
        return users, total_count

    @staticmethod
    async def get_user_activity(
        user_id: str,
        days: int = 30,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[Optional[Dict[str, Any]], int]:
        """Get a timeline of user activity"""
        if not ObjectId.is_valid(user_id):
            return None, 0
        
        # Get user info first
        user = await UserModel.get_by_id(user_id)
        if not user:
            return None, 0
        
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Combine activity from different sources
        activities = []
        
        # Note: Login and conversion tracking would be implemented when those features are added
        # For now, return basic user activity structure
        
        # Combine all activities and sort by timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        total_count = len(activities)
        activities = activities[skip:skip+limit]
        
        return {
            "user_id": user_id,
            "user_email": user["email"],
            "activity": activities,
            "total_count": total_count
        }, total_count

    @staticmethod
    async def create_password_reset_token(user_id: str) -> Optional[str]:
        """Create a password reset token for a user."""
        if not ObjectId.is_valid(user_id):
            return None
            
        # Generate a secure random token
        token = secrets.token_urlsafe(32)
        
        # Set expiration (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store token in user document
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_reset_token": token,
                    "password_reset_expires": expires_at
                }
            }
        )
        
        if result.modified_count:
            return token
        return None

    @staticmethod
    async def get_user_by_reset_token(token: str) -> Optional[dict]:
        """Get user by password reset token if valid."""
        now = datetime.utcnow()
        
        user = await users_collection.find_one({
            "password_reset_token": token,
            "password_reset_expires": {"$gt": now}
        })
        
        if user:
            user["id"] = str(user.pop("_id"))
            return user
        return None

    @staticmethod
    async def reset_password(token: str, new_password_hash: str) -> bool:
        """Reset user password using token."""
        now = datetime.utcnow()
        
        result = await users_collection.update_one(
            {
                "password_reset_token": token,
                "password_reset_expires": {"$gt": now}
            },
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "last_active": now
                },
                "$unset": {
                    "password_reset_token": "",
                    "password_reset_expires": ""
                }
            }
        )
        
        return result.modified_count > 0

    @staticmethod
    async def clear_password_reset_token(user_id: str) -> bool:
        """Clear password reset token from user."""
        if not ObjectId.is_valid(user_id):
            return False
            
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$unset": {
                    "password_reset_token": "",
                    "password_reset_expires": ""
                }
            }
        )
        
        return result.modified_count > 0