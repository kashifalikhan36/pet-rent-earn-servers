from datetime import datetime
from typing import Optional
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