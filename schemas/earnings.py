from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

class PayoutMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CRYPTO = "crypto"

class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EarningsBreakdown(BaseModel):
    total_earnings: float = Field(..., description="Total earnings to date")
    available_balance: float = Field(..., description="Available for withdrawal")
    pending_balance: float = Field(..., description="Pending from recent bookings")
    this_month_earnings: float = Field(..., description="Earnings this month")
    last_month_earnings: float = Field(..., description="Earnings last month")
    this_year_earnings: float = Field(..., description="Earnings this year")
    
    # Breakdown by source
    rental_earnings: float = Field(..., description="Earnings from pet rentals")
    bonus_earnings: float = Field(0.0, description="Bonus earnings")
    referral_earnings: float = Field(0.0, description="Earnings from referrals")
    
    # Fee breakdown
    total_fees_paid: float = Field(..., description="Total platform fees paid")
    average_fee_percentage: float = Field(..., description="Average fee percentage")
    
    # Performance metrics
    total_bookings: int = Field(..., description="Total completed bookings")
    average_booking_value: float = Field(..., description="Average booking value")
    total_pets_rented: int = Field(..., description="Number of pets rented out")

class MonthlyEarnings(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format")
    month_name: str = Field(..., description="Month name")
    total_earnings: float
    total_bookings: int
    average_booking_value: float
    fees_paid: float

class PayoutRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw")
    method: PayoutMethod = Field(..., description="Payout method")
    account_details: Dict[str, Any] = Field(..., description="Account details for payout")
    notes: Optional[str] = Field(None, description="Additional notes")

class PayoutOut(BaseModel):
    id: str
    user_id: str
    amount: float
    method: PayoutMethod
    status: PayoutStatus
    account_details: Dict[str, Any]
    processing_fee: float
    net_amount: float
    notes: Optional[str]
    requested_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    failure_reason: Optional[str]
    transaction_id: Optional[str]

class WalletDetails(BaseModel):
    current_balance: float
    available_for_withdrawal: float
    pending_balance: float
    total_earned: float
    total_withdrawn: float
    currency: str = "USD"
    
    # Recent transactions
    recent_transactions: List[Dict[str, Any]]
    
    # Payout settings
    minimum_payout: float = Field(20.0, description="Minimum amount for payout")
    payout_methods: List[PayoutMethod] = Field(default_factory=list)
    
    # Account status
    payout_enabled: bool = Field(True, description="Whether payouts are enabled")
    verification_required: bool = Field(False, description="Whether verification is needed for payout")

class EarningsResponse(BaseModel):
    earnings: EarningsBreakdown
    monthly_breakdown: List[MonthlyEarnings]
    wallet: WalletDetails
    top_performing_pets: List[Dict[str, Any]]
    earnings_trend: List[Dict[str, Any]] 