# New Owner-Related API Endpoints Documentation

**Base URL:** `https://api.cvflow.tech`

This document covers the newly implemented endpoints for enhanced owner functionality, earnings management, and analytics.

---

## 💰 Enhanced Earnings & Wallet Management

### 1. Get Detailed Wallet Information
**GET** `/api/users/wallet/detailed`
Retrieves comprehensive wallet information including recent transactions and payout settings.

```typescript
const getDetailedWalletInfo = async () => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.get('https://api.cvflow.tech/api/users/wallet/detailed', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching detailed wallet info:', error);
    throw error;
  }
};
```

**Response (200):**
```json
{
  "current_balance": 1250.75,
  "available_for_withdrawal": 1100.75,
  "pending_balance": 345.00,
  "total_earned": 5600.00,
  "total_withdrawn": 4200.00,
  "currency": "USD",
  "recent_transactions": [
    {
      "id": "txn_12345",
      "type": "credit",
      "amount": 67.50,
      "description": "Booking payment for Buddy",
      "date": "2024-01-20T10:00:00Z",
      "status": "completed"
    }
  ],
  "minimum_payout": 20.0,
  "payout_methods": ["bank_transfer", "paypal"],
  "payout_enabled": true,
  "verification_required": false
}
```

### 2. Get Detailed Earnings Breakdown
**GET** `/api/users/earnings`
Provides comprehensive earnings analytics with monthly breakdowns and performance data.

```typescript
const getDetailedEarnings = async (months: number = 12) => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.get('https://api.cvflow.tech/api/users/earnings', {
      params: { months },
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching earnings:', error);
    throw error;
  }
};
```

**Response (200):**
```json
{
  "earnings": {
    "total_earnings": 5600.00,
    "available_balance": 1100.75,
    "pending_balance": 345.00,
    "this_month_earnings": 450.00,
    "last_month_earnings": 380.00,
    "this_year_earnings": 3200.00,
    "rental_earnings": 5600.00,
    "bonus_earnings": 0.0,
    "referral_earnings": 0.0,
    "total_fees_paid": 840.00,
    "average_fee_percentage": 15.0,
    "total_bookings": 28,
    "average_booking_value": 200.00,
    "total_pets_rented": 3
  },
  "monthly_breakdown": [
    {
      "month": "2024-01",
      "month_name": "January 2024",
      "total_earnings": 450.00,
      "total_bookings": 3,
      "average_booking_value": 150.00,
      "fees_paid": 67.50
    }
  ],
  "wallet": {
    "current_balance": 1250.75,
    "available_for_withdrawal": 1100.75,
    "pending_balance": 345.00
  },
  "top_performing_pets": [
    {
      "id": "pet_12345",
      "name": "Buddy",
      "type": "dog",
      "total_bookings": 12,
      "total_earnings": 1800.00,
      "rating": 4.9
    }
  ],
  "earnings_trend": [
    {"month": "2023-12", "earnings": 380.00},
    {"month": "2024-01", "earnings": 450.00}
  ]
}
```

### 3. Request Payout/Withdrawal
**POST** `/api/users/payout`
Creates a new payout request for withdrawing earnings.

```typescript
const requestPayout = async (payoutData: {
  amount: number;
  method: 'bank_transfer' | 'paypal' | 'stripe' | 'crypto';
  account_details: {
    account_number?: string;
    routing_number?: string;
    paypal_email?: string;
    [key: string]: any;
  };
  notes?: string;
}) => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.post('https://api.cvflow.tech/api/users/payout', payoutData, {
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error requesting payout:', error);
    throw error;
  }
};
```

**Response (200):**
```json
{
  "id": "payout_12345",
  "user_id": "user_67890",
  "amount": 500.00,
  "method": "bank_transfer",
  "status": "pending",
  "account_details": {
    "account_number": "****1234",
    "routing_number": "021000021"
  },
  "processing_fee": 12.50,
  "net_amount": 487.50,
  "notes": "Regular monthly withdrawal",
  "requested_at": "2024-01-20T15:30:00Z",
  "processed_at": null,
  "completed_at": null,
  "failure_reason": null,
  "transaction_id": null
}
```

### 4. Get Payout History
**GET** `/api/users/payouts`
Retrieves the user's payout transaction history.

```typescript
const getPayoutHistory = async (page: number = 1, perPage: number = 20) => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.get('https://api.cvflow.tech/api/users/payouts', {
      params: { page, per_page: perPage },
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching payout history:', error);
    throw error;
  }
};
```

---

## 📊 Owner Analytics & Performance Metrics

### 5. Get Comprehensive Owner Analytics
**GET** `/api/users/owner-analytics`
Provides detailed analytics including performance metrics, rankings, customer analytics, and business insights.

```typescript
const getOwnerAnalytics = async () => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.get('https://api.cvflow.tech/api/users/owner-analytics', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching owner analytics:', error);
    throw error;
  }
};
```

**Response (200):**
```json
{
  "owner_metrics": {
    "total_pets_listed": 5,
    "active_pets": 4,
    "total_bookings_received": 47,
    "completed_bookings": 42,
    "acceptance_rate": 89.4,
    "response_rate": 96.2,
    "average_response_time": 2.3,
    "cancellation_rate": 4.3,
    "overall_rating": 4.7,
    "total_reviews": 28,
    "repeat_customer_rate": 45.2,
    "member_since": "2023-06-15T10:00:00Z",
    "last_booking_date": "2024-01-18T14:00:00Z",
    "most_active_month": "2023-12"
  },
  "ranking_info": {
    "performance_level": "expert",
    "ranking_score": 87.5,
    "local_ranking": 3,
    "total_owners_in_area": 24,
    "badges": ["5_star_owner", "quick_responder", "experienced_owner"],
    "next_level": "superhost",
    "requirements_for_next_level": {
      "min_rating": 4.8,
      "min_acceptance_rate": 90,
      "min_completed_bookings": 50,
      "min_response_rate": 95,
      "min_repeat_customer_rate": 50
    }
  },
  "pet_performance": [
    {
      "pet_id": "pet_12345",
      "pet_name": "Buddy",
      "pet_type": "dog",
      "total_bookings": 18,
      "total_earnings": 2700.00,
      "average_rating": 4.9,
      "total_reviews": 15,
      "view_count": 234,
      "favorite_count": 45,
      "booking_rate": 7.69,
      "last_booked": "2024-01-18T14:00:00Z",
      "performance_trend": "up"
    }
  ],
  "customer_analytics": {
    "total_unique_customers": 32,
    "repeat_customers": 14,
    "repeat_rate": 43.8,
    "average_customer_spend": 175.00,
    "top_customers": [
      {
        "customer_id": "user_98765",
        "name": "Alice Johnson",
        "total_bookings": 4,
        "total_spend": 680.00,
        "last_booking": "2024-01-15T10:00:00Z"
      }
    ],
    "customer_satisfaction_score": 4.7,
    "customer_locations": {
      "New York": 15,
      "Brooklyn": 8,
      "Queens": 5
    },
    "most_common_booking_duration": 3
  },
  "revenue_analytics": {
    "total_revenue": 5600.00,
    "monthly_revenue": [
      {"month": "2023-12", "revenue": 520.00},
      {"month": "2024-01", "revenue": 450.00}
    ],
    "revenue_by_pet": [
      {"pet_name": "Buddy", "revenue": 2700.00},
      {"pet_name": "Max", "revenue": 1800.00}
    ],
    "revenue_trend": "up",
    "peak_season_months": ["June", "July", "August"],
    "average_daily_rate": 85.00,
    "occupancy_rate": 65.0
  },
  "competitive_analysis": {
    "market_position": "above_average",
    "price_competitiveness": "competitive",
    "local_market_share": 8.5,
    "suggested_improvements": [
      "Improve response time",
      "Add more photos to listings",
      "Offer competitive pricing"
    ]
  },
  "insights": [
    "Your rating is above platform average",
    "Strong repeat customer base indicates quality service"
  ],
  "recommendations": [
    "Try to respond to messages within 1 hour",
    "Consider offering package deals for longer stays"
  ]
}
```

### 6. Get Owner Review Aggregation
**GET** `/api/users/reviews-aggregation`
Provides aggregated review data and detailed rating analytics.

```typescript
const getOwnerReviewsAggregation = async () => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.get('https://api.cvflow.tech/api/users/reviews-aggregation', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching review aggregation:', error);
    throw error;
  }
};
```

**Response (200):**
```json
{
  "overall_rating": 4.7,
  "total_reviews": 28,
  "rating_distribution": {
    "5": 18,
    "4": 7,
    "3": 2,
    "2": 1,
    "1": 0
  },
  "cleanliness_rating": 4.8,
  "communication_rating": 4.9,
  "accuracy_rating": 4.6,
  "value_rating": 4.5,
  "recent_reviews": [
    {
      "id": "review_12345",
      "rating": 5,
      "title": "Amazing experience!",
      "content": "Buddy is such a sweet dog and John was very responsive...",
      "reviewer_name": "Alice Johnson",
      "created_at": "2024-01-18T16:00:00Z"
    }
  ],
  "rating_trend": "improving",
  "reviews_per_month": [
    {
      "month": "2023-12",
      "count": 5,
      "average_rating": 4.6
    },
    {
      "month": "2024-01",
      "count": 3,
      "average_rating": 4.9
    }
  ],
  "positive_keywords": ["friendly", "clean", "responsive", "great", "excellent"],
  "improvement_areas": ["communication", "timeliness", "flexibility"]
}
```

### 7. Get Performance Metrics Summary
**GET** `/api/users/performance-metrics`
Provides a concise summary of key performance indicators.

```typescript
const getPerformanceMetrics = async () => {
  try {
    const token = localStorage.getItem('authToken');
    const response = await axios.get('https://api.cvflow.tech/api/users/performance-metrics', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching performance metrics:', error);
    throw error;
  }
};
```

**Response (200):**
```json
{
  "performance_score": 87.5,
  "performance_level": "expert",
  "acceptance_rate": 89.4,
  "response_rate": 96.2,
  "average_response_time": 2.3,
  "overall_rating": 4.7,
  "total_reviews": 28,
  "completed_bookings": 42,
  "repeat_customer_rate": 45.2,
  "local_ranking": 3,
  "badges": ["5_star_owner", "quick_responder", "experienced_owner"]
}
```

---

## 🛠️ Complete TypeScript Service Example

Here's a comprehensive TypeScript service class for all the new owner endpoints:

```typescript
// enhancedOwnerService.ts
import axios from 'axios';

const API_BASE_URL = 'https://api.cvflow.tech/api/users';

export interface PayoutRequest {
  amount: number;
  method: 'bank_transfer' | 'paypal' | 'stripe' | 'crypto';
  account_details: Record<string, any>;
  notes?: string;
}

export class EnhancedOwnerService {
  private static getAuthHeaders() {
    const token = localStorage.getItem('authToken');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  // Enhanced Wallet & Earnings
  static async getDetailedWalletInfo() {
    const response = await axios.get(`${API_BASE_URL}/wallet/detailed`, {
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  static async getDetailedEarnings(months: number = 12) {
    const response = await axios.get(`${API_BASE_URL}/earnings`, {
      params: { months },
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  static async requestPayout(payoutData: PayoutRequest) {
    const response = await axios.post(`${API_BASE_URL}/payout`, payoutData, {
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  static async getPayoutHistory(page: number = 1, perPage: number = 20) {
    const response = await axios.get(`${API_BASE_URL}/payouts`, {
      params: { page, per_page: perPage },
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  // Analytics & Performance
  static async getOwnerAnalytics() {
    const response = await axios.get(`${API_BASE_URL}/owner-analytics`, {
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  static async getReviewsAggregation() {
    const response = await axios.get(`${API_BASE_URL}/reviews-aggregation`, {
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  static async getPerformanceMetrics() {
    const response = await axios.get(`${API_BASE_URL}/performance-metrics`, {
      headers: this.getAuthHeaders()
    });
    return response.data;
  }

  // Combined dashboard data
  static async getOwnerDashboardData() {
    try {
      const [analytics, earnings, wallet, reviews] = await Promise.all([
        this.getOwnerAnalytics(),
        this.getDetailedEarnings(),
        this.getDetailedWalletInfo(),
        this.getReviewsAggregation()
      ]);

      return {
        analytics,
        earnings,
        wallet,
        reviews
      };
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      throw error;
    }
  }
}
```

---

## 📝 Usage Examples

### Dashboard Implementation
```typescript
// ownerDashboard.tsx
import { useEffect, useState } from 'react';
import { EnhancedOwnerService } from './enhancedOwnerService';

const OwnerDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const data = await EnhancedOwnerService.getOwnerDashboardData();
        setDashboardData(data);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="owner-dashboard">
      <div className="performance-section">
        <h2>Performance Level: {dashboardData.analytics.ranking_info.performance_level}</h2>
        <p>Ranking Score: {dashboardData.analytics.ranking_info.ranking_score}</p>
        <p>Local Ranking: #{dashboardData.analytics.ranking_info.local_ranking}</p>
      </div>
      
      <div className="earnings-section">
        <h2>Earnings Overview</h2>
        <p>Total Earnings: ${dashboardData.earnings.earnings.total_earnings}</p>
        <p>This Month: ${dashboardData.earnings.earnings.this_month_earnings}</p>
        <p>Available Balance: ${dashboardData.wallet.available_for_withdrawal}</p>
      </div>
      
      <div className="reviews-section">
        <h2>Reviews & Ratings</h2>
        <p>Overall Rating: {dashboardData.reviews.overall_rating}/5</p>
        <p>Total Reviews: {dashboardData.reviews.total_reviews}</p>
        <p>Rating Trend: {dashboardData.reviews.rating_trend}</p>
      </div>
    </div>
  );
};
```

### Payout Request Form
```typescript
// payoutForm.tsx
import { useState } from 'react';
import { EnhancedOwnerService } from './enhancedOwnerService';

const PayoutForm = () => {
  const [payoutData, setPayoutData] = useState({
    amount: 0,
    method: 'bank_transfer' as const,
    account_details: {},
    notes: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await EnhancedOwnerService.requestPayout(payoutData);
      alert(`Payout requested successfully! ID: ${result.id}`);
    } catch (error) {
      alert('Failed to request payout');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="number"
        placeholder="Amount"
        value={payoutData.amount}
        onChange={(e) => setPayoutData({...payoutData, amount: Number(e.target.value)})}
      />
      <select
        value={payoutData.method}
        onChange={(e) => setPayoutData({...payoutData, method: e.target.value as any})}
      >
        <option value="bank_transfer">Bank Transfer</option>
        <option value="paypal">PayPal</option>
      </select>
      <button type="submit">Request Payout</button>
    </form>
  );
};
```

These new endpoints provide comprehensive owner functionality including advanced analytics, earnings management, and performance tracking for your pet rental platform! 