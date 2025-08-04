from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import HTTPException, status

# Simple in-memory storage for rate limiting
# In production, use Redis or another distributed cache
class RateLimiter:
    def __init__(self):
        self.requests = {}  # user_id -> list of timestamps
        
    def check_rate_limit(self, user_id: str, limit: int = 5, window: int = 60) -> bool:
        """
        Check if a user has exceeded their rate limit.
        
        Args:
            user_id: The user's unique identifier
            limit: Maximum number of requests allowed in the time window
            window: Time window in seconds
            
        Returns:
            True if the request should be allowed, False if rate limited
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        # Initialize or get user's request history
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside the window
        self.requests[user_id] = [
            timestamp for timestamp in self.requests[user_id] 
            if timestamp > window_start
        ]
        
        # Check if limit is exceeded
        if len(self.requests[user_id]) >= limit:
            return False
        
        # Add current request timestamp
        self.requests[user_id].append(now)
        return True
        
    def get_remaining_requests(self, user_id: str, limit: int = 5, window: int = 60) -> int:
        """Get number of remaining requests allowed for a user."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        if user_id not in self.requests:
            return limit
            
        # Count valid requests in the current window
        valid_requests = [
            timestamp for timestamp in self.requests[user_id]
            if timestamp > window_start
        ]
        
        return max(0, limit - len(valid_requests))
        
    def get_reset_time(self, user_id: str, window: int = 60) -> Optional[datetime]:
        """Get the time when the rate limit will reset for a user."""
        if user_id not in self.requests or not self.requests[user_id]:
            return None
            
        oldest_request = min(self.requests[user_id])
        return oldest_request + timedelta(seconds=window)

# Create a global rate limiter instance
rate_limiter = RateLimiter()


# Utility function to enforce rate limits in endpoints
def check_rate_limit(user_id: str, limit: int = 5, window: int = 60):
    """
    Check if a request should be rate limited.
    Raises HTTP 429 if limit exceeded.
    """
    if not rate_limiter.check_rate_limit(user_id, limit, window):
        reset_time = rate_limiter.get_reset_time(user_id, window)
        reset_seconds = (reset_time - datetime.utcnow()).total_seconds() if reset_time else window
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {int(reset_seconds)} seconds.",
            headers={"Retry-After": str(int(reset_seconds))}
        )