from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from fastapi import Request

from schemas.notification import NotificationCreate, NotificationType, NotificationSettingsUpdate


async def create_notification(
    notification_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Create a new notification"""
    database = request.app.mongodb
    
    notification = {
        "recipient_id": notification_data["recipient_id"],
        "type": notification_data["type"],
        "title": notification_data["title"],
        "message": notification_data["message"],
        "is_read": False,
        "created_at": datetime.utcnow(),
        "read_at": None
    }
    
    # Add optional fields if present
    if "related_entity_id" in notification_data and notification_data["related_entity_id"]:
        notification["related_entity_id"] = notification_data["related_entity_id"]
        
    if "related_entity_type" in notification_data and notification_data["related_entity_type"]:
        notification["related_entity_type"] = notification_data["related_entity_type"]
        
    if "data" in notification_data and notification_data["data"]:
        notification["data"] = notification_data["data"]
    
    result = await database.notifications.insert_one(notification)
    
    if result.inserted_id:
        notification["id"] = str(result.inserted_id)
        return notification
        
    return None


async def get_user_notifications(
    user_id: str,
    request: Request,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get user notifications"""
    database = request.app.mongodb
    
    # Build query
    query = {"recipient_id": user_id}
    
    if unread_only:
        query["is_read"] = False
    
    # Get notifications
    cursor = database.notifications.find(query)
    
    # Sort by created_at in descending order (newest first)
    cursor = cursor.sort("created_at", -1)
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(limit)
    
    # Convert to list
    notifications = []
    async for notification in cursor:
        notification["id"] = str(notification.pop("_id"))
        notifications.append(notification)
    
    return notifications


async def get_notification_by_id(
    notification_id: str,
    user_id: str,
    request: Request
) -> Dict[str, Any]:
    """Get a notification by ID"""
    database = request.app.mongodb
    
    notification = await database.notifications.find_one({
        "_id": ObjectId(notification_id),
        "recipient_id": user_id
    })
    
    if notification:
        notification["id"] = str(notification.pop("_id"))
        return notification
        
    return None


async def mark_notification_as_read(
    notification_id: str,
    user_id: str,
    request: Request
) -> bool:
    """Mark a notification as read"""
    database = request.app.mongodb
    
    result = await database.notifications.update_one(
        {
            "_id": ObjectId(notification_id),
            "recipient_id": user_id,
            "is_read": False  # Only update if it's not already read
        },
        {
            "$set": {
                "is_read": True,
                "read_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


async def mark_all_notifications_as_read(
    user_id: str,
    request: Request
) -> int:
    """Mark all notifications as read"""
    database = request.app.mongodb
    
    result = await database.notifications.update_many(
        {
            "recipient_id": user_id,
            "is_read": False  # Only update unread notifications
        },
        {
            "$set": {
                "is_read": True,
                "read_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count


async def delete_notification(
    notification_id: str,
    user_id: str,
    request: Request
) -> bool:
    """Delete a notification"""
    database = request.app.mongodb
    
    result = await database.notifications.delete_one({
        "_id": ObjectId(notification_id),
        "recipient_id": user_id
    })
    
    return result.deleted_count > 0


async def get_notification_settings(
    user_id: str,
    request: Request
) -> Dict[str, Any]:
    """Get user notification settings (legacy flat structure)"""
    database = request.app.mongodb
    
    settings = await database.notification_settings.find_one({
        "user_id": user_id
    })
    
    if not settings:
        # Create default settings if not exist
        default_settings = {
            "user_id": user_id,
            "email_enabled": True,
            "push_enabled": True,
            "in_app_enabled": True,
            "booking_updates": True,
            "messages": True,
            "reviews": True,
            "payments": True,
            "system_announcements": True,
            "offers": True,
            "disputes": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await database.notification_settings.insert_one(default_settings)
        default_settings["id"] = str(default_settings.pop("_id"))
        return default_settings
        
    settings["id"] = str(settings.pop("_id"))
    return settings


async def update_notification_settings(
    user_id: str,
    settings_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Update user notification settings (legacy flat structure)"""
    database = request.app.mongodb
    
    # Remove None values
    update_data = {k: v for k, v in settings_data.items() if v is not None}
    
    if not update_data:
        return await get_notification_settings(user_id, request)
    
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    result = await database.notification_settings.update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True
    )
    
    if result.modified_count > 0 or result.upserted_id:
        return await get_notification_settings(user_id, request)
        
    return None


async def count_unread_notifications(
    user_id: str,
    request: Request
) -> int:
    """Count unread notifications for a user"""
    database = request.app.mongodb
    
    count = await database.notifications.count_documents({
        "recipient_id": user_id,
        "is_read": False
    })
    
    return count


async def create_system_notification(
    recipient_id: str,
    title: str,
    message: str,
    related_entity_id: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    request: Request = None
) -> Dict[str, Any]:
    """Create a system notification"""
    notification_data = {
        "recipient_id": recipient_id,
        "type": NotificationType.SYSTEM,
        "title": title,
        "message": message,
        "related_entity_id": related_entity_id,
        "related_entity_type": related_entity_type,
        "data": data
    }
    
    return await create_notification(notification_data, request)


# ------------------ V2 helpers for new API spec ------------------
async def get_notification_settings_v2(user_id: str, request: Request) -> Dict[str, Any]:
    """Get nested channel-based notification settings. Creates defaults if missing."""
    db = request.app.mongodb
    doc = await db.notification_settings.find_one({"user_id": user_id})
    if not doc or ("email" not in doc and "push" not in doc and "in_app" not in doc):
        # Seed defaults for v2
        v2_defaults = {
            "email": {"marketing": False, "product": True, "security": True},
            "push": {"messages": True, "offers": True, "bookings": True},
            "in_app": {"messages": True, "offers": True, "system": True},
        }
        base = {"user_id": user_id, **v2_defaults, "updated_at": datetime.utcnow()}
        if not doc:
            base["created_at"] = datetime.utcnow()
        await db.notification_settings.update_one({"user_id": user_id}, {"$set": base}, upsert=True)
        return v2_defaults
    # Build response only with nested keys
    return {
        "email": doc.get("email", {"marketing": False, "product": True, "security": True}),
        "push": doc.get("push", {"messages": True, "offers": True, "bookings": True}),
        "in_app": doc.get("in_app", {"messages": True, "offers": True, "system": True}),
    }


async def update_notification_settings_v2(user_id: str, update: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Patch nested settings. Accepts partial payload like {"email": {"marketing": true}}"""
    db = request.app.mongodb
    # Flatten nested update to $set paths
    set_ops: Dict[str, Any] = {"updated_at": datetime.utcnow()}
    for channel in ("email", "push", "in_app"):
        if channel in update and isinstance(update[channel], dict):
            for k, v in update[channel].items():
                set_ops[f"{channel}.{k}"] = v
    if len(set_ops) == 1:  # only updated_at
        # nothing to update, just return current
        return await get_notification_settings_v2(user_id, request)
    await db.notification_settings.update_one({"user_id": user_id}, {"$set": set_ops, "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()}}, upsert=True)
    return await get_notification_settings_v2(user_id, request)


async def mark_notifications_as_read_by_ids(user_id: str, ids: List[str], request: Request) -> int:
    """Mark selected notifications as read. Returns number modified."""
    db = request.app.mongodb
    object_ids = []
    for _id in ids:
        try:
            object_ids.append(ObjectId(_id))
        except Exception:
            continue
    if not object_ids:
        return 0
    res = await db.notifications.update_many(
        {"_id": {"$in": object_ids}, "recipient_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )
    return res.modified_count