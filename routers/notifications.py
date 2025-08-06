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