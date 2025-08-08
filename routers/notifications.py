from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import List, Dict, Any, Optional

from schemas.notification import NotificationOut, NotificationUpdate, NotificationSettings, NotificationSettingsUpdate
from dependencies.auth import get_current_active_user
from crud.notification import (
    get_user_notifications, get_notification_by_id, mark_notification_as_read,
    mark_all_notifications_as_read, delete_notification, count_unread_notifications,
    get_notification_settings, update_notification_settings
)
import logging
from schemas.notification import (
    NotificationFeedPage, NotificationFeedItem, NotificationReadRequest,
    NotificationSettingsV2, NotificationSettingsV2Update,
)
from crud.notification import (
    get_notification_settings_v2, update_notification_settings_v2, mark_notifications_as_read_by_ids,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[NotificationOut])
async def get_all_notifications(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_active_user)
):
    """Get all user notifications with pagination"""
    skip = (page - 1) * per_page
    user_id = current_user["id"]
    
    notifications = await get_user_notifications(
        user_id=user_id,
        request=request,
        skip=skip,
        limit=per_page
    )
    
    return notifications


# V2: feed with items + next_page
@router.get("/feed", response_model=NotificationFeedPage)
async def get_notifications_feed(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user = Depends(get_current_active_user)
):
    skip = (page - 1) * per_page
    raw = await get_user_notifications(
        user_id=current_user["id"], request=request, unread_only=unread_only, skip=skip, limit=per_page + 1
    )
    items: List[NotificationFeedItem] = []
    for n in raw[:per_page]:
        items.append(NotificationFeedItem(
            id=n["id"],
            type=str(n.get("type")),
            title=n.get("title", ""),
            body=n.get("message", ""),
            read=bool(n.get("is_read", False)),
            created_at=n.get("created_at"),
            data=n.get("data"),
        ))
    next_page = page + 1 if len(raw) > per_page else None
    return NotificationFeedPage(items=items, next_page=next_page)


@router.get("/unread", response_model=List[NotificationOut])
async def get_unread_notifications(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_active_user)
):
    """Get unread notifications with pagination"""
    skip = (page - 1) * per_page
    user_id = current_user["id"]
    
    notifications = await get_user_notifications(
        user_id=user_id,
        request=request,
        unread_only=True,
        skip=skip,
        limit=per_page
    )
    
    return notifications


@router.get("/count", response_model=Dict[str, int])
async def get_unread_count(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get count of unread notifications"""
    user_id = current_user["id"]
    
    count = await count_unread_notifications(user_id, request)
    
    return {"count": count}


@router.put("/{notification_id}/read", response_model=Dict[str, str])
async def mark_as_read(
    notification_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Mark notification as read"""
    user_id = current_user["id"]
    
    success = await mark_notification_as_read(notification_id, user_id, request)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read"
        )
    
    return {"message": "Notification marked as read"}


# V2: POST /read with ids or mark all
@router.post("/read", response_model=Dict[str, Any])
async def mark_selected_or_all_as_read(
    payload: NotificationReadRequest,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    user_id = current_user["id"]
    if payload and payload.ids:
        modified = await mark_notifications_as_read_by_ids(user_id, payload.ids, request)
        return {"message": "Selected notifications marked as read", "count": modified}
    count = await mark_all_notifications_as_read(user_id, request)
    return {"message": "All notifications marked as read", "count": count}


@router.put("/read-all", response_model=Dict[str, Any])
async def mark_all_as_read(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Mark all notifications as read"""
    user_id = current_user["id"]
    
    count = await mark_all_notifications_as_read(user_id, request)
    
    return {
        "message": "All notifications marked as read",
        "count": count
    }


@router.delete("/{notification_id}", response_model=Dict[str, str])
async def delete_notification_endpoint(
    notification_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete a notification"""
    user_id = current_user["id"]
    
    success = await delete_notification(notification_id, user_id, request)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification deleted"}


@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings_endpoint(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get user notification settings"""
    user_id = current_user["id"]
    
    settings = await get_notification_settings(user_id, request)
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification settings"
        )
    
    return settings


@router.put("/settings", response_model=NotificationSettings)
async def update_notification_settings_endpoint(
    settings: NotificationSettingsUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update notification settings"""
    user_id = current_user["id"]
    
    updated_settings = await update_notification_settings(
        user_id, 
        settings.dict(exclude_unset=True), 
        request
    )
    
    if not updated_settings:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification settings"
        )
    
    return updated_settings


# V2: nested channel-based settings
@router.get("/settings/v2", response_model=NotificationSettingsV2)
async def get_notification_settings_v2_endpoint(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    settings = await get_notification_settings_v2(current_user["id"], request)
    return NotificationSettingsV2(**settings)


@router.patch("/settings", response_model=NotificationSettingsV2)
async def patch_notification_settings_v2_endpoint(
    payload: NotificationSettingsV2Update,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    updated = await update_notification_settings_v2(current_user["id"], payload.dict(exclude_unset=True), request)
    return NotificationSettingsV2(**updated)