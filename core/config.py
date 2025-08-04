from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    # MongoDB settings
    MONGODB_URI: str
    
    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email settings for password reset and notifications
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    
    # API Base URL for full URLs in responses
    API_BASE_URL: str = "https://api.cvflow.tech"
    
    # Google OAuth settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIRECTORY: str = "uploads"
    ALLOWED_IMAGE_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_DOCUMENT_EXTENSIONS: list = [".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"]
    
    # Payment settings (Stripe/PayPal)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_MODE: str = "sandbox"  # or "live"
    
    # Platform settings
    PLATFORM_FEE_PERCENTAGE: float = 5.0  # 5% platform fee
    MIN_WALLET_BALANCE: float = 0.0
    MAX_WALLET_BALANCE: float = 10000.0
    
    # OTP settings
    OTP_EXPIRY_MINUTES: int = 15
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Push notification settings
    FCM_SERVER_KEY: str = ""
    
    # Location API settings (optional for geocoding)
    GOOGLE_MAPS_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()