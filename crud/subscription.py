from typing import Dict, Any


async def create_default_subscription(user_id: str) -> Dict[str, Any]:
    """
    Placeholder function for creating default subscription.
    This is a minimal implementation to get the application running.
    """
    # For now, just return a success response
    # In a real implementation, this would create a default subscription plan for the user
    return {
        "user_id": user_id,
        "subscription_plan": "basic",
        "status": "active",
        "created": True
    } 