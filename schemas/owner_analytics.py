from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

class PerformanceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    SUPERHOST = "superhost"

class OwnerMetrics(BaseModel):
    # Basic metrics
    total_pets_listed: int = Field(..., description="Total pets ever listed")
    active_pets: int = Field(..., description="Currently active pet listings")
    total_bookings_received: int = Field(..., description="Total bookings received")
    completed_bookings: int = Field(..., description="Successfully completed bookings")
    
    # Performance metrics
    acceptance_rate: float = Field(..., description="Booking acceptance rate (0-100)")
    response_rate: float = Field(..., description="Message response rate (0-100)")
    average_response_time: float = Field(..., description="Average response time in hours")
    cancellation_rate: float = Field(..., description="Booking cancellation rate (0-100)")
    
    # Quality metrics
    overall_rating: float = Field(..., description="Overall owner rating (1-5)")
    total_reviews: int = Field(..., description="Total reviews received")
    repeat_customer_rate: float = Field(..., description="Percentage of repeat customers")
    
    # Time-based metrics
    member_since: datetime = Field(..., description="Date when user became owner")
    last_booking_date: Optional[datetime] = Field(None, description="Date of last booking")
    most_active_month: str = Field(..., description="Month with most bookings")

class OwnerRankingInfo(BaseModel):
    performance_level: PerformanceLevel
    ranking_score: float = Field(..., description="Overall ranking score (0-100)")
    local_ranking: int = Field(..., description="Ranking in local area")
    total_owners_in_area: int = Field(..., description="Total owners in area")
    badges: List[str] = Field(default_factory=list, description="Earned badges")
    
    # Requirements for next level
    next_level: Optional[PerformanceLevel] = None
    requirements_for_next_level: Dict[str, Any] = Field(default_factory=dict)

class PetPerformance(BaseModel):
    pet_id: str
    pet_name: str
    pet_type: str
    total_bookings: int
    total_earnings: float
    average_rating: float
    total_reviews: int
    view_count: int
    favorite_count: int
    booking_rate: float = Field(..., description="Views to booking conversion rate")
    last_booked: Optional[datetime]
    performance_trend: str = Field(..., description="up/down/stable")

class CustomerAnalytics(BaseModel):
    total_unique_customers: int
    repeat_customers: int
    repeat_rate: float
    average_customer_spend: float
    top_customers: List[Dict[str, Any]]
    customer_satisfaction_score: float
    
    # Geographic data
    customer_locations: Dict[str, int] = Field(default_factory=dict)
    most_common_booking_duration: int = Field(..., description="Most common booking duration in days")

class RevenueAnalytics(BaseModel):
    total_revenue: float
    monthly_revenue: List[Dict[str, Any]]
    revenue_by_pet: List[Dict[str, Any]]
    revenue_trend: str = Field(..., description="up/down/stable")
    peak_season_months: List[str]
    average_daily_rate: float
    occupancy_rate: float = Field(..., description="Percentage of available days booked")

class CompetitiveAnalysis(BaseModel):
    market_position: str = Field(..., description="top/above_average/average/below_average")
    price_competitiveness: str = Field(..., description="expensive/competitive/cheap")
    local_market_share: float = Field(..., description="Share of local bookings")
    suggested_improvements: List[str] = Field(default_factory=list)

class OwnerAnalyticsResponse(BaseModel):
    owner_metrics: OwnerMetrics
    ranking_info: OwnerRankingInfo
    pet_performance: List[PetPerformance]
    customer_analytics: CustomerAnalytics
    revenue_analytics: RevenueAnalytics
    competitive_analysis: CompetitiveAnalysis
    
    # Insights and recommendations
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Generated at
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class OwnerReviewAggregation(BaseModel):
    overall_rating: float
    total_reviews: int
    rating_distribution: Dict[str, int]  # {"5": 45, "4": 12, etc.}
    
    # Review categories
    cleanliness_rating: float
    communication_rating: float
    accuracy_rating: float
    value_rating: float
    
    # Recent reviews
    recent_reviews: List[Dict[str, Any]]
    
    # Review trends
    rating_trend: str = Field(..., description="improving/declining/stable")
    reviews_per_month: List[Dict[str, Any]]
    
    # Common keywords from reviews
    positive_keywords: List[str] = Field(default_factory=list)
    improvement_areas: List[str] = Field(default_factory=list) 