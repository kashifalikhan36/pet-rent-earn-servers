from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, JSONResponse

from schemas.user import UserCreate, UserOut, GoogleOAuthCallback, GoogleAuthResponse, ForgotPasswordRequest, ResetPasswordRequest, PasswordResetResponse, EmailCheckResponse, UserLogin, GoogleUserInfo
from schemas.token import Token
from crud.user import create_user, authenticate_user, create_google_user, request_password_reset, reset_password_with_token, get_user_by_reset_token
from core.security import create_access_token
from core.config import get_settings
from dependencies.auth import get_current_active_user
import time
import logging
from typing import Dict, Any

settings = get_settings()
router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory cache to track used authorization codes
used_codes = {}

def is_code_used(code: str) -> bool:
    """Check if authorization code was already used"""
    current_time = time.time()
    
    # Clean up expired entries (older than 10 minutes)
    expired_codes = [c for c, t in used_codes.items() if current_time - t > 600]
    for expired_code in expired_codes:
        del used_codes[expired_code]
    
    # Check if code was used
    if code in used_codes:
        return True
    
    # Mark code as used
    used_codes[code] = current_time
    return False


@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, request: Request):
    """
    Register a new user and return an access token.
    """
    # Get client IP address and user agent for analytics
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Check if user exists, hash password, save user
    user = await create_user(user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
    )
    
    # Create JWT token and return
    token_data = {"sub": user["id"], "role": user["role"]}
    token = create_access_token(
        token_data,
        expires_delta=timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    )
    
    # Create session document
    try:
        db = request.app.mongodb
        now = __import__("datetime").datetime.utcnow()
        result = await db.sessions.insert_one({
            "user_id": user["id"],
            "ip": client_ip,
            "user_agent": user_agent,
            "created_at": now,
            "last_seen_at": now,
            "current": True,
        })
        # Mark other sessions as not current
        await db.sessions.update_many({"user_id": user["id"], "_id": {"$ne": result.inserted_id}}, {"$set": {"current": False}})
    except Exception as e:
        logger.warning(f"Failed to create session on register: {e}")
    
    return Token(access_token=token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login(request: Request):
    """
    Unified login endpoint that accepts both JSON and form data.
    
    JSON format: {"email": "user@example.com", "password": "password"}
    Form format: username=user@example.com&password=password
    """
    try:
        # Get content type
        content_type = request.headers.get("content-type", "")
        
        email = None
        password = None
        
        if "application/json" in content_type:
            # Handle JSON request
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
            
            if not email or not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email and password are required for JSON login"
                )
                
            logger.debug(f"JSON login attempt for email: {email}")
            
        elif "application/x-www-form-urlencoded" in content_type:
            # Handle form data
            form = await request.form()
            email = form.get("username") or form.get("email")  # Support both fields
            password = form.get("password")
            
            if not email or not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username/email and password are required for form login"
                )
                
            logger.debug(f"Form login attempt for email: {email}")
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content-Type must be application/json or application/x-www-form-urlencoded"
            )
        
        # Get client IP address and user agent for analytics
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Authenticate user
        user = await authenticate_user(email, password)
        
        if not user:
            logger.warning(f"Authentication failed for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Authentication successful for user: {user['email']}")
        
        # Create access token
        token_data = {"sub": user["id"], "role": user["role"]}
        token = create_access_token(
            token_data,
            expires_delta=timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
        )
        
        # Create or update session document
        try:
            db = request.app.mongodb
            now = __import__("datetime").datetime.utcnow()
            existing = await db.sessions.find_one({"user_id": user["id"], "ip": client_ip, "user_agent": user_agent})
            if existing:
                await db.sessions.update_one({"_id": existing["_id"]}, {"$set": {"last_seen_at": now, "current": True}})
                current_id = existing["_id"]
            else:
                res = await db.sessions.insert_one({
                    "user_id": user["id"],
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "created_at": now,
                    "last_seen_at": now,
                    "current": True,
                })
                current_id = res.inserted_id
            await db.sessions.update_many({"user_id": user["id"], "_id": {"$ne": current_id}}, {"$set": {"current": False}})
        except Exception as e:
            logger.warning(f"Failed to create/update session on login: {e}")
        
        return Token(access_token=token, token_type="bearer")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout():
    """
    Client-side logout - no server-side action needed for JWT.
    """
    return {"detail": "Successfully logged out"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(current_user = Depends(get_current_active_user)):
    """
    Refresh JWT token for authenticated user.
    """
    # Create new access token
    token_data = {"sub": current_user["id"], "role": current_user["role"]}
    token = create_access_token(
        token_data,
        expires_delta=timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    )
        
    return Token(access_token=token, token_type="bearer")


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset for user.
    Sends reset email if user exists.
    """
    try:
        success = await request_password_reset(request.email)
        
        if success:
            return PasswordResetResponse(
                message="If the email exists in our system, a password reset link has been sent.",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
            
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset user password using token.
    """
    try:
        # Verify token and get user
        user = await get_user_by_reset_token(request.token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Reset password
        success = await reset_password_with_token(request.token, request.new_password)
        
        if success:
            return PasswordResetResponse(
                message="Password has been reset successfully.",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.get("/me", response_model=UserOut)
async def get_current_user(current_user = Depends(get_current_active_user)):
    """
    Get the current authenticated user's information.
    """
    return current_user


# GOOGLE OAUTH ENDPOINTS
@router.get("/google", response_model=GoogleAuthResponse)
async def google_auth():
    """
    Get Google OAuth authorization URL.
    """
    try:
        # Check if Google OAuth is configured
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured. Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET."
            )
        
        from utils.google_oauth import GoogleOAuth
        auth_url = GoogleOAuth.get_google_auth_url()
        return GoogleAuthResponse(auth_url=auth_url)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error in google_auth: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Google auth URL: {str(e)}"
        )


@router.post("/google/login", response_model=Token)
async def google_login(
    callback_data: GoogleOAuthCallback,
    request: Request
):
    """
    Professional Google OAuth login endpoint that returns JWT token directly.
    Use this for API clients that want a JSON response instead of redirect.
    """
    try:
        # Check if Google OAuth is configured
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured"
            )
        
        # Check if authorization code was already used
        if is_code_used(callback_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code has already been used"
            )
        
        logger.info(f"Google login received code: {callback_data.code[:20]}...")
        
        # Exchange code for tokens
        from utils.google_oauth import GoogleOAuth
        token_data = await GoogleOAuth.exchange_code_for_token(callback_data.code)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        # Get user info from ID token
        user_info = None
        if "id_token" in token_data:
            user_info = await GoogleOAuth.get_user_info_from_token(token_data["id_token"])
        
        # If ID token failed, try access token
        if not user_info and "access_token" in token_data:
            user_info = await GoogleOAuth.get_user_info_from_access_token(token_data["access_token"])
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google"
            )
        
        logger.info(f"Google login user info: {user_info['email']}")
        
        # Create or get user
        user = await create_google_user(
            name=user_info["name"],
            email=user_info["email"],
            google_id=user_info["id"],
            profile_picture=user_info.get("picture")
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve user"
            )
        
        # Create JWT token
        token_payload = {"sub": user["id"], "role": user["role"]}
        access_token = create_access_token(
            token_payload,
            expires_delta=timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
        )
        
        # Create or update session document
        try:
            db = request.app.mongodb
            now = __import__("datetime").datetime.utcnow()
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")
            existing = await db.sessions.find_one({"user_id": user["id"], "ip": client_ip, "user_agent": user_agent})
            if existing:
                await db.sessions.update_one({"_id": existing["_id"]}, {"$set": {"last_seen_at": now, "current": True}})
                current_id = existing["_id"]
            else:
                res = await db.sessions.insert_one({
                    "user_id": user["id"],
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "created_at": now,
                    "last_seen_at": now,
                    "current": True,
                })
                current_id = res.inserted_id
            await db.sessions.update_many({"user_id": user["id"], "_id": {"$ne": current_id}}, {"$set": {"current": False}})
        except Exception as e:
            logger.warning(f"Failed to create/update session on google login: {e}")
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Google login error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    request: Request = None
):
    """
    Handle Google OAuth callback and redirect to frontend.
    Use this for web applications that need redirect-based flow.
    """
    # Get client IP address and user agent for analytics
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    try:
        # Check if Google OAuth is configured
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth not configured - missing credentials")
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=oauth_not_configured"
            return RedirectResponse(url=error_url)
        
        # Check if authorization code was already used
        if is_code_used(code):
            logger.warning(f"Authorization code already used in callback: {code[:20]}...")
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=code_already_used"
            return RedirectResponse(url=error_url)
        
        logger.info(f"Google callback received code: {code[:20]}...")
        
        # Exchange code for tokens
        from utils.google_oauth import GoogleOAuth
        token_data = await GoogleOAuth.exchange_code_for_token(code)
        if not token_data:
            logger.error("Token exchange failed in callback")
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=token_exchange_failed"
            return RedirectResponse(url=error_url)
        
        logger.info(f"Callback token exchange successful: {list(token_data.keys())}")
        
        # Get user info from ID token
        user_info = None
        if "id_token" in token_data:
            user_info = await GoogleOAuth.get_user_info_from_token(token_data["id_token"])
        
        # If ID token failed, try access token
        if not user_info and "access_token" in token_data:
            user_info = await GoogleOAuth.get_user_info_from_access_token(token_data["access_token"])
        
        if not user_info:
            logger.error("Failed to get user info in callback")
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=user_info_failed"
            return RedirectResponse(url=error_url)
        
        logger.info(f"Callback user info: {user_info['email']}")
        
        # Create or get user
        user = await create_google_user(
            name=user_info["name"],
            email=user_info["email"],
            google_id=user_info["id"],
            profile_picture=user_info.get("picture")
        )
        
        if not user:
            logger.error(f"Failed to create user in callback: {user_info['email']}")
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=user_creation_failed"
            return RedirectResponse(url=error_url)
        
        # Create JWT token
        token_payload = {"sub": user["id"], "role": user["role"]}
        access_token = create_access_token(
            token_payload,
            expires_delta=timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
        )
        
        # Create or update session document
        try:
            db = request.app.mongodb
            now = __import__("datetime").datetime.utcnow()
            existing = await db.sessions.find_one({"user_id": user["id"], "ip": client_ip, "user_agent": user_agent})
            if existing:
                await db.sessions.update_one({"_id": existing["_id"]}, {"$set": {"last_seen_at": now, "current": True}})
                current_id = existing["_id"]
            else:
                res = await db.sessions.insert_one({
                    "user_id": user["id"],
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "created_at": now,
                    "last_seen_at": now,
                    "current": True,
                })
                current_id = res.inserted_id
            await db.sessions.update_many({"user_id": user["id"], "_id": {"$ne": current_id}}, {"$set": {"current": False}})
        except Exception as e:
            logger.warning(f"Failed to create/update session on google callback: {e}")
        
        # Redirect to frontend with token
        redirect_url = f"{settings.FRONTEND_URL}/auth/success?token={access_token}"
        logger.info(f"Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        import traceback
        error_msg = f"Callback error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        error_url = f"{settings.FRONTEND_URL}/auth/error?message=authentication_failed"
        return RedirectResponse(url=error_url)


@router.get("/google/user-info", response_model=GoogleUserInfo)
async def get_google_user_info(
    access_token: str = Query(..., description="Google access token")
):
    """
    Get Google user information using access token.
    This endpoint can be used to verify Google tokens or get user info.
    """
    try:
        from utils.google_oauth import GoogleOAuth
        user_info = await GoogleOAuth.get_user_info_from_access_token(access_token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired Google access token"
            )
        
        return GoogleUserInfo(**user_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information from Google"
        )


@router.get("/verify-reset-token/{token}")
async def verify_reset_token(token: str):
    """
    Verify if reset token is valid and not expired.
    """
    try:
        user = await get_user_by_reset_token(token)
        if user:
            return {
                "valid": True,
                "message": "Token is valid"
            }
        else:
            return {
                "valid": False,
                "message": "Invalid or expired token"
            }
            
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        return {
            "valid": False,
            "message": "Failed to verify token"
        }