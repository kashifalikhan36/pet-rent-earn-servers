from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse

from schemas.user import UserOut, UserProfileUpdate, WalletUpdate, VerificationSubmission, UserDetailedOut, UserDashboardAnalytics
from schemas.earnings import EarningsResponse, PayoutRequest, PayoutOut, WalletDetails
from schemas.owner_analytics import OwnerAnalyticsResponse, OwnerReviewAggregation
from dependencies.auth import get_current_active_user
from crud.user import (
    get_user_by_id_with_request, update_user_profile_basic, upload_user_avatar, 
    update_wallet_balance, submit_verification_documents, get_verification_status,
    get_detailed_user_profile, get_user_dashboard_analytics
)
from crud.earnings import (
    get_user_earnings_breakdown, get_monthly_earnings_breakdown, get_detailed_wallet_info,
    create_payout_request, get_user_payouts, get_top_performing_pets
)
from crud.owner_analytics import (
    get_owner_metrics, get_owner_ranking_info, get_pet_performance_analytics,
    get_customer_analytics, get_owner_review_aggregation
)
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


@router.get("/dashboard-analytics", response_model=UserDashboardAnalytics)
async def get_dashboard_analytics(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get detailed dashboard analytics for current user"""
    user_id = current_user["id"]
    analytics = await get_user_dashboard_analytics(user_id, request)
    
    return analytics


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


@router.get("/profile/detailed", response_model=UserDetailedOut)
async def get_detailed_profile(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get detailed profile with stats for current user"""
    user_id = current_user["id"]
    detailed_profile = await get_detailed_user_profile(user_id, request)
    
    if not detailed_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return detailed_profile


@router.get("/{user_id}/profile", response_model=UserDetailedOut)
async def get_user_detailed_profile(
    user_id: str,
    request: Request
):
    """Get detailed public profile for any user"""
    detailed_profile = await get_detailed_user_profile(user_id, request)
    
    if not detailed_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove sensitive information for public profiles
    if "email" in detailed_profile:
        del detailed_profile["email"]
    if "wallet_balance" in detailed_profile:
        del detailed_profile["wallet_balance"]
        
    return detailed_profile


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


# Enhanced wallet endpoints
@router.get("/wallet/detailed", response_model=WalletDetails)
async def get_detailed_wallet_info_endpoint(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get detailed wallet information including recent transactions"""
    wallet_info = await get_detailed_wallet_info(current_user["id"], request)
    
    if not wallet_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet information not found"
        )
    
    return wallet_info


# Earnings endpoints
@router.get("/earnings", response_model=EarningsResponse)
async def get_detailed_earnings(
    request: Request,
    months: int = Query(12, ge=1, le=24, description="Number of months for breakdown"),
    current_user = Depends(get_current_active_user)
):
    """Get detailed earnings breakdown with monthly data and analytics"""
    user_id = current_user["id"]
    
    # Get earnings breakdown
    earnings = await get_user_earnings_breakdown(user_id, request)
    
    # Get monthly breakdown
    monthly_breakdown = await get_monthly_earnings_breakdown(user_id, request, months)
    
    # Get wallet details
    wallet = await get_detailed_wallet_info(user_id, request)
    
    # Get top performing pets
    top_performing_pets = await get_top_performing_pets(user_id, request, limit=5)
    
    # Create earnings trend data
    earnings_trend = [
        {
            "month": month_data["month"],
            "earnings": month_data["total_earnings"]
        }
        for month_data in monthly_breakdown
    ]
    
    return {
        "earnings": earnings,
        "monthly_breakdown": monthly_breakdown,
        "wallet": wallet,
        "top_performing_pets": top_performing_pets,
        "earnings_trend": earnings_trend
    }


# Payout endpoints
@router.post("/payout", response_model=PayoutOut)
async def request_payout(
    payout_request: PayoutRequest,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Request a payout/withdrawal"""
    user_id = current_user["id"]
    
    payout = await create_payout_request(
        user_id=user_id,
        amount=payout_request.amount,
        method=payout_request.method,
        account_details=payout_request.account_details,
        notes=payout_request.notes,
        request=request
    )
    
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create payout request"
        )
    
    if "error" in payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=payout["error"]
        )
    
    return payout


@router.get("/payouts", response_model=List[PayoutOut])
async def get_user_payouts_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get user's payout history"""
    user_id = current_user["id"]
    skip = (page - 1) * per_page
    
    payouts = await get_user_payouts(user_id, request, limit=per_page, skip=skip)
    
    return payouts


# Owner analytics endpoints
@router.get("/owner-analytics", response_model=OwnerAnalyticsResponse)
async def get_owner_analytics(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get comprehensive owner analytics and performance metrics"""
    user_id = current_user["id"]
    
    # Get all analytics components
    owner_metrics = await get_owner_metrics(user_id, request)
    ranking_info = await get_owner_ranking_info(user_id, request)
    pet_performance = await get_pet_performance_analytics(user_id, request)
    customer_analytics = await get_customer_analytics(user_id, request)
    
    # Calculate revenue analytics
    earnings = await get_user_earnings_breakdown(user_id, request)
    monthly_earnings = await get_monthly_earnings_breakdown(user_id, request, 12)
    
    revenue_analytics = {
        "total_revenue": earnings.get("total_earnings", 0),
        "monthly_revenue": [
            {
                "month": month["month"],
                "revenue": month["total_earnings"]
            }
            for month in monthly_earnings
        ],
        "revenue_by_pet": [
            {
                "pet_name": pet["pet_name"],
                "revenue": pet["total_earnings"]
            }
            for pet in pet_performance[:5]
        ],
        "revenue_trend": "up" if earnings.get("this_month_earnings", 0) > earnings.get("last_month_earnings", 0) else "stable",
        "peak_season_months": ["June", "July", "August"],  # Simplified
        "average_daily_rate": sum(pet.get("total_earnings", 0) for pet in pet_performance) / max(sum(pet.get("total_bookings", 0) for pet in pet_performance), 1),
        "occupancy_rate": 65.0  # Simplified calculation
    }
    
    # Competitive analysis (simplified)
    competitive_analysis = {
        "market_position": "above_average" if ranking_info.get("ranking_score", 0) > 70 else "average",
        "price_competitiveness": "competitive",
        "local_market_share": min(10.0, 100.0 / max(ranking_info.get("total_owners_in_area", 1), 1)),
        "suggested_improvements": [
            "Improve response time",
            "Add more photos to listings",
            "Offer competitive pricing"
        ]
    }
    
    # Generate insights and recommendations
    insights = []
    recommendations = []
    
    if owner_metrics.get("overall_rating", 0) < 4.0:
        insights.append("Your rating is below the platform average")
        recommendations.append("Focus on improving service quality to increase ratings")
    
    if owner_metrics.get("response_rate", 0) < 90:
        insights.append("Your response rate could be improved")
        recommendations.append("Try to respond to messages within 1 hour")
    
    if len(pet_performance) == 1:
        recommendations.append("Consider adding more pets to increase your earning potential")
    
    return {
        "owner_metrics": owner_metrics,
        "ranking_info": ranking_info,
        "pet_performance": pet_performance,
        "customer_analytics": customer_analytics,
        "revenue_analytics": revenue_analytics,
        "competitive_analysis": competitive_analysis,
        "insights": insights,
        "recommendations": recommendations
    }


@router.get("/reviews-aggregation", response_model=OwnerReviewAggregation)
async def get_owner_reviews_aggregation(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get aggregated review data and ratings for the owner"""
    user_id = current_user["id"]
    
    review_data = await get_owner_review_aggregation(user_id, request)
    
    return review_data


@router.get("/performance-metrics")
async def get_owner_performance_metrics(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get specific performance metrics for the owner"""
    user_id = current_user["id"]
    
    metrics = await get_owner_metrics(user_id, request)
    ranking = await get_owner_ranking_info(user_id, request)
    
    return {
        "performance_score": ranking.get("ranking_score", 0),
        "performance_level": ranking.get("performance_level", "beginner"),
        "acceptance_rate": metrics.get("acceptance_rate", 0),
        "response_rate": metrics.get("response_rate", 0),
        "average_response_time": metrics.get("average_response_time", 0),
        "overall_rating": metrics.get("overall_rating", 0),
        "total_reviews": metrics.get("total_reviews", 0),
        "completed_bookings": metrics.get("completed_bookings", 0),
        "repeat_customer_rate": metrics.get("repeat_customer_rate", 0),
        "local_ranking": ranking.get("local_ranking", 0),
        "badges": ranking.get("badges", [])
    } 