from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class UserBase(BaseModel):
    """Base schema with common user attributes."""
    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for user creation with password."""
    password: str

    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserOut(UserBase):
    """Schema for user output data."""
    id: str
    role: str
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    wallet_balance: float = 0.0
    verification_status: str = "unverified"
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for admin updating user role."""
    role: str

    @validator('role')
    def valid_role(cls, v):
        if v not in ['user', 'admin']:
            raise ValueError('Role must be either "user" or "admin"')
        return v


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: str
    new_password: Optional[str] = None

    @validator('new_password')
    def password_min_length(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request."""
    token: str
    new_password: str

    @validator('new_password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class PasswordResetResponse(BaseModel):
    """Schema for password reset response."""
    message: str
    success: bool


class GoogleOAuthCallback(BaseModel):
    """Schema for Google OAuth callback."""
    code: str
    state: Optional[str] = None


class GoogleAuthResponse(BaseModel):
    """Schema for Google authentication response."""
    auth_url: str


class GoogleUserInfo(BaseModel):
    """Schema for Google user information."""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = False


class EmailCheckResponse(BaseModel):
    """Schema for email check response."""
    exists: bool
    can_reset: bool
    message: str
    next_step: Optional[str] = None


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PAYMENT = "payment"
    REFUND = "refund"
    EARNING = "earning"


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)


class WalletUpdate(BaseModel):
    """Schema for wallet balance update."""
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    description: Optional[str] = Field(None, max_length=200)


class VerificationSubmission(BaseModel):
    """Schema for verification document submission."""
    id_document_url: str
    address_document_url: str
    additional_info: Optional[str] = None


class UserDetailedOut(BaseModel):
    """Schema for detailed user profile output with stats."""
    email: Optional[EmailStr] = None
    total_pets: int = 0
    active_pets: int = 0
    average_rating: float = 0.0
    review_count: int = 0
    response_rate: float = 0.0
    response_time: int = 0  # Average response time in minutes
    member_since: datetime
    verified_id: bool = False
    verified_phone: bool = False
    verified_email: bool = False
    total_bookings: int = 0
    completion_rate: float = 100.0
    languages: list[str] = []
    social_links: dict = Field(default_factory=dict)


class OwnerProfileOut(BaseModel):
    """Schema for pet owner profile details."""
    id: str
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    verification_status: str
    average_rating: float = 0.0
    review_count: int = 0
    response_rate: float = 0.0
    response_time: int = 0  # Average response time in minutes
    member_since: datetime
    total_pets: int = 0
    languages: list[str] = []
    completion_rate: float = 100.0


class UserPreferences(BaseModel):
    """Schema for user preferences."""
    preferred_pet_types: list[str] = []
    preferred_locations: list[str] = []
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    notifications_enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    newsletter_subscription: bool = False
    dark_mode: bool = False
    language: str = "en"
    currency: str = "USD"


class UserDashboardAnalytics(BaseModel):
    """Schema for user dashboard analytics."""
    total_earnings: float = 0.0
    pending_earnings: float = 0.0
    active_bookings: int = 0
    pending_requests: int = 0
    completed_bookings: int = 0
    cancelled_bookings: int = 0
    profile_views: int = 0
    pet_views: int = 0
    inquiry_response_rate: float = 0.0
    average_response_time: int = 0  # minutes
    bookings_last_30_days: int = 0
    earnings_last_30_days: float = 0.0
    completion_rate: float = 100.0


class RecentActivity(BaseModel):
    """Schema for recent activity."""
    id: str
    activity_type: str  # message, booking, review, view, favorite, etc.
    entity_type: str  # pet, user, booking, etc.
    entity_id: str
    timestamp: datetime
    message: str
    read: bool = False
    data: dict = Field(default_factory=dict)


class NotificationOut(BaseModel):
    """Schema for notification."""
    id: str
    title: str
    message: str
    type: str  # message, booking, review, system, etc.
    created_at: datetime
    read: bool = False
    action_url: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


class UserVerificationRequest(BaseModel):
    """Schema for user verification request."""
    id_type: str  # passport, driver_license, national_id
    address_type: str  # utility_bill, bank_statement, etc.
    additional_info: Optional[str] = None


class UserReport(BaseModel):
    """Schema for user reporting."""
    reported_user_id: str
    report_type: str  # inappropriate, fraud, harassment, etc.
    description: str
    evidence_urls: list[str] = []


# ---- New schemas for Profile & Settings spec ----
class Gender(str, Enum):
    male = "male"
    female = "female"
    non_binary = "non_binary"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class SocialLinks(BaseModel):
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None


class LocationPublic(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


class MeProfileOut(BaseModel):
    id: str
    email: EmailStr
    username: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[Gender] = None
    location: Optional[LocationPublic] = None
    links: Optional[SocialLinks] = None


class MeProfilePatch(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    birthdate: Optional[date] = None
    gender: Optional[Gender] = None
    location: Optional[LocationPublic] = None
    links: Optional[SocialLinks] = None


class PublicLocation(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None


class PublicUserOut(BaseModel):
    id: str
    username: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[PublicLocation] = None
    links: Optional[SocialLinks] = None


class UsernameAvailabilityResponse(BaseModel):
    available: bool
    suggestions: Optional[List[str]] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @validator('new_password')
    def password_min_length_v2(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class ProfileVisibility(str, Enum):
    public = "public"
    private = "private"


class AllowMessagesFrom(str, Enum):
    everyone = "everyone"
    following = "following"
    none = "none"


class PrivacySettings(BaseModel):
    profile_visibility: ProfileVisibility = ProfileVisibility.public
    discoverable_by_email: bool = True
    discoverable_by_phone: bool = False
    allow_messages_from: AllowMessagesFrom = AllowMessagesFrom.everyone


class PrivacySettingsUpdate(BaseModel):
    profile_visibility: Optional[ProfileVisibility] = None
    discoverable_by_email: Optional[bool] = None
    discoverable_by_phone: Optional[bool] = None
    allow_messages_from: Optional[AllowMessagesFrom] = None


class BlockedUserOut(BaseModel):
    user_id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    blocked_at: datetime


class AddressOut(BaseModel):
    id: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    is_default: bool = False


class AddressCreate(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    is_default: Optional[bool] = False


class AddressUpdate(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None


class SessionOut(BaseModel):
    id: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    current: bool = False