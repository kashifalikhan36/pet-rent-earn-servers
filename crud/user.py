from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from models.user import UserModel
from schemas.user import UserCreate, ProfileUpdate, UserProfileUpdate, VerificationSubmission, WalletUpdate
from core.security import hash_password, verify_password
from crud.subscription import create_default_subscription
from utils.mailer import email_service


async def create_user(user_in: UserCreate) -> Dict[str, Any]:
    """Create a new user."""
    # Check if user exists
    existing_user = await get_user_by_email(user_in.email)
    if existing_user:
        return None
        
    # Hash password and create user
    hashed_password = hash_password(user_in.password)
    user = await UserModel.create(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_password
    )
    
    # Create default Premium subscription for new user
    if user:
        await create_default_subscription(user["id"])
    
    return user


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    return await UserModel.get_by_email(email)


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    return await UserModel.get_by_id(user_id)


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user by email and password."""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


async def update_user_profile(user_id: str, payload: ProfileUpdate) -> Optional[Dict[str, Any]]:
    """Update user profile."""
    user = await get_user_by_id(user_id)
    if not user:
        return None
        
    # Verify current password
    if not verify_password(payload.current_password, user["password_hash"]):
        return None
        
    # Prepare update data
    update_data = {}
    if payload.name:
        update_data["name"] = payload.name
    if payload.email:
        # Check if email is already taken by another user
        existing = await get_user_by_email(payload.email)
        if existing and existing["id"] != user_id:
            return None
        update_data["email"] = payload.email.lower()
    if payload.new_password:
        update_data["password_hash"] = hash_password(payload.new_password)
        
    if not update_data:
        return user  # No changes
        
    return await UserModel.update(user_id, update_data)


async def get_all_users(page: int = 1, limit: int = 20) -> Tuple[List[Dict[str, Any]], int]:
    """Get all users with pagination."""
    skip = (page - 1) * limit
    return await UserModel.list(skip, limit)


async def update_user_role(user_id: str, role: str) -> Optional[Dict[str, Any]]:
    """Update a user's role."""
    if role not in ["user", "admin"]:
        return None
    return await UserModel.update(user_id, {"role": role})


async def delete_user(user_id: str) -> bool:
    """Delete a user."""
    return await UserModel.delete(user_id)


async def create_google_user(name: str, email: str, google_id: str, profile_picture: str = None) -> Dict[str, Any]:
    """Create a new user from Google OAuth."""
    # Check if user already exists by email
    existing_user = await get_user_by_email(email)
    if existing_user:
        # If user exists but doesn't have Google ID, link the account
        if not existing_user.get("google_id"):
            update_data = {
                "google_id": google_id,
                "oauth_provider": "google"
            }
            if profile_picture:
                update_data["profile_picture"] = profile_picture
            
            return await UserModel.update(existing_user["id"], update_data)
        return existing_user
    
    # Check if user exists by Google ID
    existing_google_user = await get_user_by_google_id(google_id)
    if existing_google_user:
        return existing_google_user
    
    # Create new user
    user = await UserModel.create(
        name=name,
        email=email,
        google_id=google_id,
        profile_picture=profile_picture
    )
    
    # Create default Premium subscription for new user
    if user:
        await create_default_subscription(user["id"])
    
    return user


async def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Google ID."""
    return await UserModel.get_by_google_id(google_id)


async def request_password_reset(email: str) -> bool:
    """Request password reset for user."""
    user = await get_user_by_email(email)
    if not user:
        # Don't reveal if user exists or not for security
        return True
    
    # Don't allow password reset for Google OAuth users
    if user.get("google_id"):
        return True
    
    # Create password reset token
    token = await UserModel.create_password_reset_token(user["id"])
    if not token:
        return False
    
    # Send password reset email
    success = email_service.send_password_reset_email(
        user_email=user["email"],
        user_name=user["name"],
        reset_token=token
    )
    
    # If email fails, clear the token
    if not success:
        await UserModel.clear_password_reset_token(user["id"])
        return False
    
    return True


async def reset_password_with_token(token: str, new_password: str) -> bool:
    """Reset password using token."""
    # Hash the new password
    hashed_password = hash_password(new_password)
    
    # Reset password with token
    success = await UserModel.reset_password(token, hashed_password)
    
    return success


async def get_user_by_reset_token(token: str) -> Optional[Dict[str, Any]]:
    """Get user by reset token."""
    return await UserModel.get_user_by_reset_token(token)


async def get_user_by_id(user_id: str, request) -> Optional[Dict[str, Any]]:
    """Get user by ID with request context."""
    database = request.app.mongodb
    from bson import ObjectId
    try:
        user = await database.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["id"] = str(user["_id"])
            del user["_id"]
        return user
    except Exception:
        return None


async def update_user_profile(user_id: str, user_data: UserProfileUpdate, request) -> Optional[Dict[str, Any]]:
    """Update user profile with new data."""
    database = request.app.mongodb
    from bson import ObjectId
    
    try:
        # Convert to dict and exclude None values
        update_dict = {k: v for k, v in user_data.dict().items() if v is not None}
        
        if not update_dict:
            return await get_user_by_id(user_id, request)
        
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count > 0:
            return await get_user_by_id(user_id, request)
        return None
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return None


async def upload_user_avatar(user_id: str, avatar_url: str, request) -> bool:
    """Update user avatar URL."""
    database = request.app.mongodb
    from bson import ObjectId
    
    try:
        result = await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "avatar_url": avatar_url,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        return False


async def update_wallet_balance(user_id: str, amount: float, transaction_type: str, description: str, request) -> Optional[Dict[str, Any]]:
    """Update user wallet balance."""
    database = request.app.mongodb
    from bson import ObjectId
    
    try:
        # Get current user to check balance
        user = await get_user_by_id(user_id, request)
        if not user:
            return None
        
        current_balance = user.get("wallet_balance", 0.0)
        
        # Calculate new balance based on transaction type
        if transaction_type in ["deposit", "refund", "earning"]:
            new_balance = current_balance + amount
        elif transaction_type in ["withdrawal", "payment"]:
            new_balance = current_balance - amount
            if new_balance < 0:
                return None  # Insufficient funds
        else:
            return None  # Invalid transaction type
        
        # Update balance
        result = await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "wallet_balance": new_balance,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Log transaction
            await database.wallet_transactions.insert_one({
                "user_id": user_id,
                "amount": amount,
                "transaction_type": transaction_type,
                "description": description,
                "previous_balance": current_balance,
                "new_balance": new_balance,
                "created_at": datetime.utcnow()
            })
            
            return {"new_balance": new_balance}
        return None
    except Exception as e:
        print(f"Error updating wallet balance: {e}")
        return None


async def submit_verification_documents(user_id: str, verification_data: VerificationSubmission, request) -> bool:
    """Submit verification documents for user."""
    database = request.app.mongodb
    from bson import ObjectId
    
    try:
        # Create verification record
        verification_record = {
            "user_id": user_id,
            "id_document_url": verification_data.id_document_url,
            "address_document_url": verification_data.address_document_url,
            "additional_info": verification_data.additional_info,
            "status": "pending",
            "submitted_at": datetime.utcnow(),
            "reviewed_at": None,
            "reviewer_id": None,
            "rejection_reason": None
        }
        
        await database.verifications.insert_one(verification_record)
        
        # Update user verification status
        result = await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "verification_status": "pending",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"Error submitting verification: {e}")
        return False


async def get_verification_status(user_id: str, request) -> Dict[str, Any]:
    """Get user verification status."""
    database = request.app.mongodb
    
    try:
        verification = await database.verifications.find_one(
            {"user_id": user_id},
            sort=[("submitted_at", -1)]  # Get latest submission
        )
        
        if not verification:
            return {"status": "unverified"}
        
        return {
            "status": verification.get("status", "unverified"),
            "submitted_at": verification.get("submitted_at"),
            "reviewed_at": verification.get("reviewed_at"),
            "rejection_reason": verification.get("rejection_reason")
        }
    except Exception as e:
        print(f"Error getting verification status: {e}")
        return {"status": "unverified"}