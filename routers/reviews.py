from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, File, UploadFile, Form
from typing import List, Dict, Any, Optional

from schemas.review import (
    ReviewCreate, ReviewOut, ReviewType, ReviewSummary, 
    ReviewUpdate, ReviewFilter, ReviewHelpful, ReviewReport
)
from dependencies.auth import get_current_active_user
from crud.review import (
    create_review, update_review, delete_review, get_review_by_id,
    get_entity_reviews, get_user_reviews, get_reviews_summary,
    mark_review_helpful, report_review, get_pending_review_opportunities
)
from utils.file_upload import upload_image_file
import logging
from bson import ObjectId

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{entity_type}/{entity_id}", response_model=ReviewOut)
async def create_review_endpoint(
    entity_id: str,
    entity_type: ReviewType,
    review: ReviewCreate,
    request: Request,
    transaction_id: Optional[str] = Query(None),
    current_user = Depends(get_current_active_user)
):
    """Create a review for a user or pet"""
    # Get user info
    user_id = current_user["id"]
    user_name = current_user.get("name", "Anonymous User")
    user_avatar = current_user.get("avatar_url")
    
    # Ensure user cannot review themselves
    if entity_type == ReviewType.USER and entity_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot review yourself"
        )
    
    # Create review
    created_review = await create_review(
        entity_id=entity_id,
        entity_type=entity_type,
        review_data=review.dict(),
        reviewer_id=user_id,
        reviewer_name=user_name,
        reviewer_avatar=user_avatar,
        transaction_id=transaction_id,
        request=request
    )
    
    if not created_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create review. You may have already reviewed this entity or it doesn't exist."
        )
    
    return created_review


@router.put("/{review_id}", response_model=ReviewOut)
async def update_review_endpoint(
    review_id: str,
    review_update: ReviewUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update a review"""
    user_id = current_user["id"]
    
    updated_review = await update_review(
        review_id=review_id,
        update_data=review_update.dict(exclude_unset=True),
        user_id=user_id,
        request=request
    )
    
    if not updated_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission to update it"
        )
    
    return updated_review


@router.delete("/{review_id}")
async def delete_review_endpoint(
    review_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete a review"""
    user_id = current_user["id"]
    
    success = await delete_review(
        review_id=review_id,
        user_id=user_id,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission to delete it"
        )
    
    return {"message": "Review deleted successfully"}


@router.get("/{entity_type}/{entity_id}", response_model=List[ReviewOut])
async def get_entity_reviews_endpoint(
    entity_id: str,
    entity_type: ReviewType,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    request: Request = None
):
    """Get reviews for an entity with filters"""
    skip = (page - 1) * per_page
    
    reviews = await get_entity_reviews(
        entity_id=entity_id,
        entity_type=entity_type,
        skip=skip,
        limit=per_page,
        min_rating=min_rating,
        max_rating=max_rating,
        sort_by=sort_by,
        sort_order=sort_order,
        request=request
    )
    
    return reviews


@router.get("/{entity_type}/{entity_id}/summary", response_model=ReviewSummary)
async def get_entity_reviews_summary_endpoint(
    entity_id: str,
    entity_type: ReviewType,
    request: Request
):
    """Get summary of reviews for an entity"""
    summary = await get_reviews_summary(
        entity_id=entity_id,
        entity_type=entity_type,
        request=request
    )
    
    return summary


@router.get("/user/{user_id}/written", response_model=List[ReviewOut])
async def get_user_written_reviews_endpoint(
    user_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get reviews written by a user"""
    # Only allow users to see their own written reviews
    if current_user["id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own written reviews"
        )
    
    skip = (page - 1) * per_page
    
    reviews = await get_user_reviews(
        user_id=user_id,
        as_reviewer=True,
        skip=skip,
        limit=per_page,
        request=request
    )
    
    return reviews


@router.get("/pending-opportunities", response_model=List[Dict[str, Any]])
async def get_pending_review_opportunities_endpoint(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get pending review opportunities for completed transactions"""
    user_id = current_user["id"]
    
    opportunities = await get_pending_review_opportunities(
        user_id=user_id,
        request=request
    )
    
    return opportunities


@router.post("/{review_id}/helpful")
async def mark_review_helpful_endpoint(
    review_id: str,
    helpful_data: ReviewHelpful,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Mark a review as helpful or unhelpful"""
    user_id = current_user["id"]
    
    success = await mark_review_helpful(
        review_id=review_id,
        user_id=user_id,
        helpful=helpful_data.helpful,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to mark review. Review not found or you're trying to mark your own review."
        )
    
    action = "marked as helpful" if helpful_data.helpful else "unmarked as helpful"
    return {"message": f"Review {action} successfully"}


@router.post("/{review_id}/report")
async def report_review_endpoint(
    review_id: str,
    report_data: ReviewReport,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Report a review for inappropriate content"""
    user_id = current_user["id"]
    
    success = await report_review(
        review_id=review_id,
        user_id=user_id,
        reason=report_data.reason,
        details=report_data.details,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to report review. Review not found or you're trying to report your own review."
        )
    
    return {"message": "Review reported successfully"}


@router.post("/{review_id}/images")
async def upload_review_images(
    review_id: str,
    request: Request,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_active_user)
):
    """Upload images for a review"""
    user_id = current_user["id"]
    
    # Check if review exists and belongs to user
    review = await get_review_by_id(review_id, request)
    
    if not review or review["reviewer_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission to upload images"
        )
    
    # Check file types
    for file in files:
        content_type = file.content_type
        if not content_type or not content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not an image"
            )
    
    # Upload images
    image_urls = []
    for file in files:
        try:
            image_url = await upload_image_file(file, "reviews")
            image_urls.append(image_url)
        except Exception as e:
            logger.error(f"Failed to upload review image: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image: {str(e)}"
            )
    
    # Update review with new images
    database = request.app.mongodb
    
    current_images = review.get("images", [])
    updated_images = current_images + image_urls
    
    await database.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {"images": updated_images}}
    )
    
    return {
        "message": f"{len(image_urls)} images uploaded successfully",
        "images": image_urls
    } 