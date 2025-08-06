from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bson import ObjectId
from fastapi import Request, HTTPException, status

from schemas.report import ReportEntityType, ReportStatusType


async def create_report(
    entity_id: str,
    entity_type: ReportEntityType,
    reporter_id: str,
    reason: str,
    details: Optional[str] = None,
    evidence_urls: Optional[list[str]] = None,
    request: Request = None
) -> Dict[str, Any]:
    """
    Create a new report for an entity
    """
    database = request.app.mongodb
    
    # Check if entity exists
    entity_data = None
    
    if entity_type == ReportEntityType.USER:
        entity = await database.users.find_one({"_id": ObjectId(entity_id)})
        if entity:
            entity_data = {
                "user_name": entity.get("name", ""),
                "user_email": entity.get("email", ""),
                "user_joined_at": entity.get("created_at", "")
            }
    
    elif entity_type == ReportEntityType.PET:
        entity = await database.pets.find_one({"_id": ObjectId(entity_id)})
        if entity:
            entity_data = {
                "pet_name": entity.get("name", ""),
                "pet_type": entity.get("type", ""),
                "pet_breed": entity.get("breed", ""),
                "owner_id": entity.get("owner_id", "")
            }
    
    elif entity_type == ReportEntityType.REVIEW:
        entity = await database.reviews.find_one({"_id": ObjectId(entity_id)})
        if entity:
            entity_data = {
                "review_text": entity.get("comment", ""),
                "review_rating": entity.get("rating", ""),
                "reviewer_id": entity.get("reviewer_id", ""),
                "entity_id": entity.get("entity_id", ""),
                "entity_type": entity.get("entity_type", "")
            }
    
    elif entity_type == ReportEntityType.MESSAGE:
        entity = await database.messages.find_one({"_id": ObjectId(entity_id)})
        if entity:
            entity_data = {
                "message_text": entity.get("text", ""),
                "sender_id": entity.get("sender_id", ""),
                "conversation_id": entity.get("conversation_id", "")
            }
    
    # For other entity types, you can add more checks here
    
    if not entity:
        return None
        
    # Check if user has already reported this entity
    existing_report = await database.reports.find_one({
        "reporter_id": reporter_id,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "status": {"$in": [ReportStatusType.PENDING, ReportStatusType.INVESTIGATING]}
    })
    
    if existing_report:
        # Update the existing report with new details if provided
        if details:
            await database.reports.update_one(
                {"_id": existing_report["_id"]},
                {"$set": {
                    "details": details,
                    "updated_at": datetime.utcnow()
                }}
            )
        
        return None  # User already reported this entity
    
    # Create report
    now = datetime.utcnow()
    report = {
        "reporter_id": reporter_id,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "reason": reason,
        "details": details,
        "evidence_urls": evidence_urls or [],
        "status": ReportStatusType.PENDING,
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
        "admin_notes": None,
        "entity_data": entity_data
    }
    
    result = await database.reports.insert_one(report)
    
    if not result.inserted_id:
        return None
        
    report["id"] = str(result.inserted_id)
    
    return report


async def get_user_reports(
    user_id: str,
    request: Request,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get all reports created by a user
    """
    database = request.app.mongodb
    
    # Get reports
    cursor = database.reports.find({"reporter_id": user_id})
    
    # Sort by created_at in descending order (newest first)
    cursor = cursor.sort("created_at", -1)
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(limit)
    
    # Convert to list
    reports = []
    async for report in cursor:
        report["id"] = str(report.pop("_id"))
        reports.append(report)
    
    return reports


async def get_report_by_id(
    report_id: str,
    user_id: str,
    request: Request,
    admin_only: bool = False
) -> Dict[str, Any]:
    """
    Get a report by ID (only reporter or admin can view)
    """
    database = request.app.mongodb
    
    # Check user role
    user = await database.users.find_one({"_id": ObjectId(user_id)})
    is_admin = user and user.get("role") == "admin"
    
    if admin_only and not is_admin:
        return None
    
    query = {"_id": ObjectId(report_id)}
    
    # If not admin, can only view own reports
    if not is_admin:
        query["reporter_id"] = user_id
    
    report = await database.reports.find_one(query)
    
    if report:
        report["id"] = str(report.pop("_id"))
        return report
        
    return None


async def update_report_status(
    report_id: str,
    status: ReportStatusType,
    admin_notes: Optional[str],
    admin_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Update a report status (admin only)
    """
    database = request.app.mongodb
    
    # Verify admin permission
    admin = await database.users.find_one({
        "_id": ObjectId(admin_id),
        "role": "admin"
    })
    
    if not admin:
        return None
    
    # Prepare update
    update_dict = {
        "status": status,
        "updated_at": datetime.utcnow(),
    }
    
    if admin_notes:
        update_dict["admin_notes"] = admin_notes
    
    if status in [ReportStatusType.RESOLVED, ReportStatusType.DISMISSED]:
        update_dict["resolved_at"] = datetime.utcnow()
    
    # Update report
    result = await database.reports.update_one(
        {"_id": ObjectId(report_id)},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        return None
    
    # Get updated report
    updated_report = await database.reports.find_one({"_id": ObjectId(report_id)})
    
    if updated_report:
        updated_report["id"] = str(updated_report.pop("_id"))
        
        # If status changed to resolved, create notification for reporter
        if status == ReportStatusType.RESOLVED:
            try:
                from crud.notification import create_notification
                from schemas.notification import NotificationType
                
                # Get reporter ID
                reporter_id = updated_report.get("reporter_id")
                
                if reporter_id:
                    # Create notification data
                    notification_data = {
                        "recipient_id": reporter_id,
                        "type": NotificationType.SYSTEM,
                        "title": "Report Resolution",
                        "message": f"Your report has been resolved. Thank you for helping keep our platform safe.",
                        "related_entity_id": report_id,
                        "related_entity_type": "report",
                        "data": {
                            "report_id": report_id,
                            "report_status": status
                        }
                    }
                    
                    await create_notification(notification_data, request)
            except Exception as e:
                print(f"Failed to create notification: {str(e)}")
    
    return updated_report


async def get_all_reports(
    request: Request,
    status: Optional[ReportStatusType] = None,
    entity_type: Optional[ReportEntityType] = None,
    skip: int = 0,
    limit: int = 20
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get all reports (admin only) with optional filters
    """
    database = request.app.mongodb
    
    # Build query
    query = {}
    
    if status:
        query["status"] = status
        
    if entity_type:
        query["entity_type"] = entity_type
    
    # Count total matching reports
    total_count = await database.reports.count_documents(query)
    
    # Get reports with pagination
    cursor = database.reports.find(query)
    
    # Sort by status (pending first) and then by created date (newest first)
    cursor = cursor.sort([
        ("status", 1),  # 1 = ascending (pending first, then investigating, etc.)
        ("created_at", -1)  # -1 = descending (newest first)
    ])
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(limit)
    
    # Convert to list
    reports = []
    async for report in cursor:
        report["id"] = str(report.pop("_id"))
        reports.append(report)
    
    return reports, total_count


async def delete_report(
    report_id: str,
    user_id: str,
    request: Request
) -> bool:
    """
    Delete a report (only reporter or admin can delete)
    """
    database = request.app.mongodb
    
    # Check user role
    user = await database.users.find_one({"_id": ObjectId(user_id)})
    is_admin = user and user.get("role") == "admin"
    
    query = {"_id": ObjectId(report_id)}
    
    # If not admin, can only delete own reports
    if not is_admin:
        query["reporter_id"] = user_id
    
    result = await database.reports.delete_one(query)
    
    return result.deleted_count > 0 