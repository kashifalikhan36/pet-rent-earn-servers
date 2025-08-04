from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse

from schemas.user import UserOut, UserProfileUpdate, WalletUpdate, VerificationSubmission
from dependencies.auth import get_current_active_user
from crud.user import get_user_by_id_with_request, update_user_profile_basic, upload_user_avatar, update_wallet_balance, submit_verification_documents, get_verification_status
from utils.file_upload import upload_image_file, upload_document_file
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/profile", response_model=UserOut)
async def get_current_user_profile(
    current_user = Depends(get_current_active_user)
):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserOut)
async def update_user_profile_endpoint(
    user_data: UserProfileUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update user profile"""
    updated_user = await update_user_profile_basic(current_user["id"], user_data, request)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
    
    return updated_user


@router.post("/upload-avatar")
async def upload_user_avatar_endpoint(
    request: Request,
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user)
):
    """Upload user profile picture"""
    try:
        # Upload file
        file_url = await upload_image_file(file, "avatars")
        
        # Update user profile with new avatar
        success = await upload_user_avatar(current_user["id"], file_url, request)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update avatar"
            )
        
        return {
            "detail": "Avatar uploaded successfully",
            "avatar_url": file_url
        }
        
    except Exception as e:
        logger.error(f"Error uploading avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar"
        )


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get dashboard statistics for current user"""
    try:
        database = request.app.mongodb
        user_id = current_user["id"]
        
        # Get user's pet listings count
        pets_count = await database.pets.count_documents({"owner_id": user_id})
        active_pets_count = await database.pets.count_documents({
            "owner_id": user_id, 
            "status": "active"
        })
        
        # Get total views across all user's pets
        pipeline = [
            {"$match": {"owner_id": user_id}},
            {"$group": {"_id": None, "total_views": {"$sum": "$view_count"}}}
        ]
        total_views_result = await database.pets.aggregate(pipeline).to_list(1)
        total_views = total_views_result[0]["total_views"] if total_views_result else 0
        
        # Get total favorites across all user's pets  
        pipeline = [
            {"$match": {"owner_id": user_id}},
            {"$group": {"_id": None, "total_favorites": {"$sum": "$favorite_count"}}}
        ]
        total_favorites_result = await database.pets.aggregate(pipeline).to_list(1)
        total_favorites = total_favorites_result[0]["total_favorites"] if total_favorites_result else 0
        
        return {
            "total_pets": pets_count,
            "active_pets": active_pets_count,
            "total_views": total_views,
            "total_favorites": total_favorites,
            "total_earnings": 0.0,  # TODO: Implement when transactions are added
            "pending_bookings": 0,  # TODO: Implement when bookings are added
            "recent_activity_count": 0  # TODO: Implement activity tracking
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard statistics"
        )


@router.get("/verification-status")
async def get_user_verification_status(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get user verification status"""
    verification_status = await get_verification_status(current_user["id"], request)
    
    return {
        "status": verification_status.get("status", "unverified"),
        "submitted_at": verification_status.get("submitted_at"),
        "reviewed_at": verification_status.get("reviewed_at"),
        "rejection_reason": verification_status.get("rejection_reason"),
        "documents_required": verification_status.get("documents_required", [
            "government_id",
            "proof_of_address"
        ])
    }


@router.get("/wallet/balance")
async def get_wallet_balance(
    current_user = Depends(get_current_active_user)
):
    """Get user wallet balance"""
    return {
        "balance": current_user.get("wallet_balance", 0.0),
        "currency": "USD"  # This could be configurable
    }


@router.get("/{user_id}", response_model=UserOut)
async def get_public_user_profile(
    user_id: str,
    request: Request
):
    """Get public user profile"""
    user = await get_user_by_id_with_request(user_id, request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return only public information
    public_user = {
        "id": user["id"],
        "name": user["name"],
        "avatar_url": user.get("avatar_url"),
        "created_at": user["created_at"],
        "verification_status": user.get("verification_status", "unverified"),
        # Don't include sensitive information like email, wallet_balance, etc.
    }
    
    return public_user


@router.put("/wallet", response_model=Dict[str, Any])
async def update_user_wallet(
    wallet_data: WalletUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update wallet balance (admin only or through payment integration)"""
    # This endpoint would typically be restricted to admin users or payment webhook
    # For now, we'll allow users to update their own wallet for testing
    
    success = await update_wallet_balance(
        current_user["id"], 
        wallet_data.amount, 
        wallet_data.transaction_type,
        wallet_data.description,
        request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update wallet balance"
        )
    
    return {
        "detail": "Wallet balance updated successfully",
        "new_balance": success.get("new_balance", 0)
    }


@router.post("/submit-verification")
async def submit_user_verification(
    request: Request,
    id_document: UploadFile = File(..., description="Government ID document"),
    address_document: UploadFile = File(..., description="Proof of address document"),
    additional_info: Optional[str] = Form(None, description="Additional information"),
    current_user = Depends(get_current_active_user)
):
    """Submit verification documents"""
    try:
        # Upload documents
        id_document_url = await upload_document_file(id_document, "verification")
        address_document_url = await upload_document_file(address_document, "verification")
        
        # Submit verification
        verification_data = VerificationSubmission(
            id_document_url=id_document_url,
            address_document_url=address_document_url,
            additional_info=additional_info
        )
        
        success = await submit_verification_documents(
            current_user["id"], 
            verification_data, 
            request
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit verification documents"
            )
        
        return {
            "detail": "Verification documents submitted successfully",
            "status": "pending_review"
        }
        
    except Exception as e:
        logger.error(f"Error submitting verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit verification documents"
        ) 