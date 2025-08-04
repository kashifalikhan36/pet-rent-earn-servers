from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from pydantic import ValidationError
from datetime import datetime
import logging

from core.config import get_settings
from schemas.token import TokenPayload
from crud.user import get_user_by_id

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Decode JWT token and return the current user.
    Raises 401 if token is invalid or user not found.
    """
    logger.debug(f"Attempting to validate token: {token[:20]}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        logger.debug("Decoding JWT token...")
        
        # Decode the token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        logger.debug(f"Token payload: {payload}")
        
        # Validate payload structure
        token_data = TokenPayload(**payload)
        logger.debug(f"Token data validation successful: sub={token_data.sub}, role={token_data.role}")
        
        # Check token expiration
        if payload.get("exp") and datetime.utcnow().timestamp() > payload["exp"]:
            logger.error("Token has expired")
            raise credentials_exception
            
        # Get the user ID from sub claim
        user_id = token_data.sub
        if user_id is None:
            logger.error("No user ID found in token")
            raise credentials_exception
            
        logger.debug(f"Looking up user with ID: {user_id}")
        
    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise credentials_exception
    except ValidationError as e:
        logger.error(f"Token validation error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {str(e)}")
        raise credentials_exception
        
    # Get the user from database
    user = await get_user_by_id(user_id)
    if user is None:
        logger.error(f"User not found in database: {user_id}")
        raise credentials_exception
        
    logger.debug(f"Authentication successful for user: {user.get('email', 'unknown')}")
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Return the current active user.
    Could implement additional checks here in the future.
    """
    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Return the current user if they have admin role.
    Raises 403 if the user is not an admin.
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user