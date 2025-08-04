import json
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
from google.auth.transport import requests
from google.oauth2 import id_token
from core.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


class GoogleOAuth:
    """Google OAuth utility class for handling authentication"""
    
    @staticmethod
    def get_google_auth_url() -> str:
        """Generate Google OAuth authorization URL"""
        try:
            base_url = "https://accounts.google.com/o/oauth2/auth"
            params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "scope": "openid email profile",
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent"
            }
            
            # Properly URL encode the query parameters
            query_string = urlencode(params)
            auth_url = f"{base_url}?{query_string}"
            logger.info(f"Generated Google auth URL: {auth_url}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating Google auth URL: {str(e)}")
            raise
    
    @staticmethod
    async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                logger.info("Successfully exchanged code for token")
                return token_data
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error during token exchange: {e.response.status_code} - {e.response.text}")
                return None
            except httpx.TimeoutException:
                logger.error("Timeout during token exchange")
                return None
            except Exception as e:
                logger.error(f"Unexpected error during token exchange: {str(e)}")
                return None
    
    @staticmethod
    async def get_user_info_from_token(id_token_str: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google ID token"""
        try:
            # Verify the token
            request = requests.Request()
            id_info = id_token.verify_oauth2_token(
                id_token_str, request, settings.GOOGLE_CLIENT_ID
            )
            
            # Verify the issuer
            if id_info["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                logger.warning(f"Invalid token issuer: {id_info['iss']}")
                return None
            
            user_info = {
                "id": id_info["sub"],
                "email": id_info["email"],
                "name": id_info.get("name", ""),
                "picture": id_info.get("picture", ""),
                "email_verified": id_info.get("email_verified", False)
            }
            logger.info(f"Successfully extracted user info from ID token for user: {user_info['email']}")
            return user_info
            
        except ValueError as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during ID token verification: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_info_from_access_token(access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information using access token"""
        user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(user_info_url)
                response.raise_for_status()
                user_data = response.json()
                
                user_info = {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name", ""),
                    "picture": user_data.get("picture", ""),
                    "email_verified": user_data.get("verified_email", False)
                }
                logger.info(f"Successfully retrieved user info from access token for user: {user_info['email']}")
                return user_info
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error during user info retrieval: {e.response.status_code} - {e.response.text}")
                return None
            except httpx.TimeoutException:
                logger.error("Timeout during user info retrieval")
                return None
            except Exception as e:
                logger.error(f"Unexpected error during user info retrieval: {str(e)}")
                return None 