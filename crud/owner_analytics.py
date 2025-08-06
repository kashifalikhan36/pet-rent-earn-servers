from typing import Optional, List, Dict, Any
from fastapi import Request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)

async def get_owner_metrics(user_id: str, request: Request) -> Dict[str, Any]:
    """Get comprehensive owner performance metrics"""
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Get user info
        user = await database.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {}
        
        # Basic metrics
        total_pets_listed = await database.pets.count_documents({"owner_id": user_id})
        active_pets = await database.pets.count_documents({"owner_id": user_id, "status": "active"})
        
        # Booking metrics
        total_bookings_received = await database.bookings.count_documents({"owner_id": user_id})
        completed_bookings = await database.bookings.count_documents({"owner_id": user_id, "status": "completed"})
        
        # Calculate acceptance rate
        pending_bookings = await database.bookings.count_documents({
            "owner_id": user_id, 
            "status": {"$in": ["pending", "confirmed", "rejected"]}
        })
        confirmed_bookings = await database.bookings.count_documents({
            "owner_id": user_id,
            "status": "confirmed"
        })
        acceptance_rate = (confirmed_bookings / max(pending_bookings, 1)) * 100
        
        # Get conversation response metrics
        conversations = await database.conversations.find({
            "participants": user_id
        }).to_list(None)
        
        # Calculate response rate and time (simplified)
        total_messages_received = 0
        total_responses = 0
        response_times = []
        
        for conv in conversations:
            messages = await database.messages.find({
                "conversation_id": str(conv.get("_id"))
            }).sort("timestamp", 1).to_list(None)
            
            user_messages = [m for m in messages if m.get("sender_id") == user_id]
            other_messages = [m for m in messages if m.get("sender_id") != user_id]
            
            if user_messages and other_messages:
                total_messages_received += len(other_messages)
                total_responses += len(user_messages)
                
                # Calculate average response time for first responses
                for i, other_msg in enumerate(other_messages):
                    next_user_msg = next((m for m in user_messages if m.get("timestamp", datetime.min) > other_msg.get("timestamp", datetime.min)), None)
                    if next_user_msg:
                        time_diff = next_user_msg.get("timestamp", datetime.min) - other_msg.get("timestamp", datetime.min)
                        response_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
        
        response_rate = (total_responses / max(total_messages_received, 1)) * 100
        average_response_time = sum(response_times) / max(len(response_times), 1)
        
        # Calculate cancellation rate
        cancelled_bookings = await database.bookings.count_documents({
            "owner_id": user_id,
            "status": "cancelled"
        })
        cancellation_rate = (cancelled_bookings / max(total_bookings_received, 1)) * 100
        
        # Get reviews and ratings
        reviews = await database.reviews.find({
            "entity_type": "user",
            "entity_id": user_id
        }).to_list(None)
        
        overall_rating = sum(r.get("rating", 0) for r in reviews) / max(len(reviews), 1)
        total_reviews = len(reviews)
        
        # Calculate repeat customer rate
        all_bookings = await database.bookings.find({
            "owner_id": user_id,
            "status": "completed"
        }).to_list(None)
        
        unique_customers = set(b.get("renter_id") for b in all_bookings)
        repeat_customers = 0
        for customer_id in unique_customers:
            customer_bookings = [b for b in all_bookings if b.get("renter_id") == customer_id]
            if len(customer_bookings) > 1:
                repeat_customers += 1
        
        repeat_customer_rate = (repeat_customers / max(len(unique_customers), 1)) * 100
        
        # Get last booking date
        last_booking = await database.bookings.find_one({
            "owner_id": user_id,
            "status": "completed"
        }, sort=[("end_date", -1)])
        
        last_booking_date = last_booking.get("end_date") if last_booking else None
        
        # Find most active month
        from collections import Counter
        booking_months = [b.get("start_date", datetime.min).strftime("%Y-%m") for b in all_bookings if b.get("start_date")]
        most_active_month = Counter(booking_months).most_common(1)[0][0] if booking_months else "N/A"
        
        return {
            "total_pets_listed": total_pets_listed,
            "active_pets": active_pets,
            "total_bookings_received": total_bookings_received,
            "completed_bookings": completed_bookings,
            "acceptance_rate": round(acceptance_rate, 1),
            "response_rate": round(response_rate, 1),
            "average_response_time": round(average_response_time, 1),
            "cancellation_rate": round(cancellation_rate, 1),
            "overall_rating": round(overall_rating, 1),
            "total_reviews": total_reviews,
            "repeat_customer_rate": round(repeat_customer_rate, 1),
            "member_since": user.get("created_at"),
            "last_booking_date": last_booking_date,
            "most_active_month": most_active_month
        }
    
    except Exception as e:
        logger.error(f"Error getting owner metrics for user {user_id}: {str(e)}")
        return {}

async def get_owner_ranking_info(user_id: str, request: Request) -> Dict[str, Any]:
    """Get owner ranking and performance level information"""
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Get user location for local ranking
        user = await database.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {}
        
        user_city = user.get("location", {}).get("city", "")
        
        # Get owner metrics first
        metrics = await get_owner_metrics(user_id, request)
        
        # Calculate ranking score based on multiple factors
        score_components = {
            "rating": min(metrics.get("overall_rating", 0) * 20, 100),  # Max 100 for 5-star rating
            "acceptance_rate": min(metrics.get("acceptance_rate", 0), 100),
            "response_rate": min(metrics.get("response_rate", 0), 100),
            "completed_bookings": min(metrics.get("completed_bookings", 0) * 2, 100),  # 2 points per booking, max 100
            "repeat_customers": min(metrics.get("repeat_customer_rate", 0), 100)
        }
        
        ranking_score = sum(score_components.values()) / len(score_components)
        
        # Determine performance level
        if ranking_score >= 90:
            performance_level = "superhost"
            next_level = None
        elif ranking_score >= 75:
            performance_level = "expert"
            next_level = "superhost"
        elif ranking_score >= 60:
            performance_level = "advanced"
            next_level = "expert"
        elif ranking_score >= 40:
            performance_level = "intermediate"
            next_level = "advanced"
        else:
            performance_level = "beginner"
            next_level = "intermediate"
        
        # Calculate local ranking
        local_owners = await database.users.find({
            "location.city": user_city,
            "role": {"$in": ["user", "owner"]}
        }).to_list(None)
        
        # Calculate scores for all local owners (simplified)
        owner_scores = []
        for owner in local_owners:
            owner_metrics = await get_owner_metrics(str(owner.get("_id")), request)
            owner_score = (
                owner_metrics.get("overall_rating", 0) * 20 +
                owner_metrics.get("acceptance_rate", 0) +
                owner_metrics.get("response_rate", 0) +
                owner_metrics.get("completed_bookings", 0) * 2
            ) / 4
            owner_scores.append((str(owner.get("_id")), owner_score))
        
        # Sort by score and find user's rank
        owner_scores.sort(key=lambda x: x[1], reverse=True)
        local_ranking = next((i + 1 for i, (owner_id, score) in enumerate(owner_scores) if owner_id == user_id), len(owner_scores))
        
        # Determine badges
        badges = []
        if metrics.get("overall_rating", 0) >= 4.8:
            badges.append("5_star_owner")
        if metrics.get("response_rate", 0) >= 95:
            badges.append("quick_responder")
        if metrics.get("completed_bookings", 0) >= 10:
            badges.append("experienced_owner")
        if metrics.get("repeat_customer_rate", 0) >= 50:
            badges.append("customer_favorite")
        if performance_level == "superhost":
            badges.append("superhost")
        
        # Requirements for next level
        requirements = {}
        if next_level:
            if next_level == "intermediate":
                requirements = {
                    "min_rating": 3.5,
                    "min_acceptance_rate": 70,
                    "min_completed_bookings": 5
                }
            elif next_level == "advanced":
                requirements = {
                    "min_rating": 4.0,
                    "min_acceptance_rate": 80,
                    "min_completed_bookings": 15,
                    "min_response_rate": 85
                }
            elif next_level == "expert":
                requirements = {
                    "min_rating": 4.5,
                    "min_acceptance_rate": 85,
                    "min_completed_bookings": 25,
                    "min_response_rate": 90,
                    "min_repeat_customer_rate": 30
                }
            elif next_level == "superhost":
                requirements = {
                    "min_rating": 4.8,
                    "min_acceptance_rate": 90,
                    "min_completed_bookings": 50,
                    "min_response_rate": 95,
                    "min_repeat_customer_rate": 50
                }
        
        return {
            "performance_level": performance_level,
            "ranking_score": round(ranking_score, 1),
            "local_ranking": local_ranking,
            "total_owners_in_area": len(local_owners),
            "badges": badges,
            "next_level": next_level,
            "requirements_for_next_level": requirements
        }
    
    except Exception as e:
        logger.error(f"Error getting ranking info for user {user_id}: {str(e)}")
        return {}

async def get_pet_performance_analytics(user_id: str, request: Request) -> List[Dict[str, Any]]:
    """Get performance analytics for all user's pets"""
    try:
        database = request.app.mongodb
        
        # Get all user's pets
        pets = await database.pets.find({"owner_id": user_id}).to_list(None)
        
        pet_performance = []
        for pet in pets:
            pet_id = str(pet.get("_id"))
            
            # Get booking statistics
            bookings = await database.bookings.find({
                "pet_id": pet_id,
                "status": "completed"
            }).to_list(None)
            
            total_bookings = len(bookings)
            total_earnings = sum(b.get("total_amount", 0) * 0.85 for b in bookings)  # After platform fees
            
            # Get reviews
            reviews = await database.reviews.find({
                "entity_id": pet_id,
                "entity_type": "pet"
            }).to_list(None)
            
            average_rating = sum(r.get("rating", 0) for r in reviews) / max(len(reviews), 1)
            total_reviews = len(reviews)
            
            # Get view and favorite counts
            view_count = pet.get("view_count", 0)
            favorite_count = pet.get("favorite_count", 0)
            
            # Calculate booking rate (views to booking conversion)
            booking_rate = (total_bookings / max(view_count, 1)) * 100
            
            # Get last booking date
            last_booking = max(bookings, key=lambda x: x.get("end_date", datetime.min)) if bookings else None
            last_booked = last_booking.get("end_date") if last_booking else None
            
            # Determine performance trend (simplified)
            recent_bookings = [b for b in bookings if (datetime.utcnow() - b.get("start_date", datetime.min)).days <= 90]
            older_bookings = [b for b in bookings if (datetime.utcnow() - b.get("start_date", datetime.min)).days > 90]
            
            recent_count = len(recent_bookings)
            older_count = len(older_bookings)
            
            if recent_count > older_count:
                performance_trend = "up"
            elif recent_count < older_count:
                performance_trend = "down"
            else:
                performance_trend = "stable"
            
            pet_performance.append({
                "pet_id": pet_id,
                "pet_name": pet.get("name", ""),
                "pet_type": pet.get("type", ""),
                "total_bookings": total_bookings,
                "total_earnings": total_earnings,
                "average_rating": round(average_rating, 1),
                "total_reviews": total_reviews,
                "view_count": view_count,
                "favorite_count": favorite_count,
                "booking_rate": round(booking_rate, 2),
                "last_booked": last_booked,
                "performance_trend": performance_trend
            })
        
        # Sort by total earnings descending
        pet_performance.sort(key=lambda x: x["total_earnings"], reverse=True)
        
        return pet_performance
    
    except Exception as e:
        logger.error(f"Error getting pet performance for user {user_id}: {str(e)}")
        return []

async def get_customer_analytics(user_id: str, request: Request) -> Dict[str, Any]:
    """Get customer analytics for an owner"""
    try:
        database = request.app.mongodb
        
        # Get all completed bookings
        bookings = await database.bookings.find({
            "owner_id": user_id,
            "status": "completed"
        }).to_list(None)
        
        if not bookings:
            return {
                "total_unique_customers": 0,
                "repeat_customers": 0,
                "repeat_rate": 0.0,
                "average_customer_spend": 0.0,
                "top_customers": [],
                "customer_satisfaction_score": 0.0,
                "customer_locations": {},
                "most_common_booking_duration": 0
            }
        
        # Calculate customer metrics
        from collections import Counter, defaultdict
        
        customer_data = defaultdict(list)
        for booking in bookings:
            renter_id = booking.get("renter_id")
            if renter_id:
                customer_data[renter_id].append(booking)
        
        total_unique_customers = len(customer_data)
        repeat_customers = sum(1 for bookings_list in customer_data.values() if len(bookings_list) > 1)
        repeat_rate = (repeat_customers / max(total_unique_customers, 1)) * 100
        
        # Calculate average customer spend
        total_spend = sum(b.get("total_amount", 0) for b in bookings)
        average_customer_spend = total_spend / max(total_unique_customers, 1)
        
        # Get top customers
        top_customers = []
        for customer_id, customer_bookings in customer_data.items():
            customer_spend = sum(b.get("total_amount", 0) for b in customer_bookings)
            
            # Get customer info
            customer = await database.users.find_one({"_id": customer_id})
            if customer:
                top_customers.append({
                    "customer_id": customer_id,
                    "name": customer.get("full_name", ""),
                    "total_bookings": len(customer_bookings),
                    "total_spend": customer_spend,
                    "last_booking": max(customer_bookings, key=lambda x: x.get("start_date", datetime.min)).get("start_date")
                })
        
        top_customers.sort(key=lambda x: x["total_spend"], reverse=True)
        top_customers = top_customers[:5]  # Top 5 customers
        
        # Calculate customer satisfaction (based on reviews)
        all_reviews = await database.reviews.find({
            "entity_type": "user",
            "entity_id": user_id
        }).to_list(None)
        
        customer_satisfaction_score = sum(r.get("rating", 0) for r in all_reviews) / max(len(all_reviews), 1)
        
        # Get customer locations (simplified)
        customer_locations = {}
        for customer_id in customer_data.keys():
            customer = await database.users.find_one({"_id": customer_id})
            if customer and customer.get("location", {}).get("city"):
                city = customer["location"]["city"]
                customer_locations[city] = customer_locations.get(city, 0) + 1
        
        # Calculate most common booking duration
        durations = []
        for booking in bookings:
            if booking.get("start_date") and booking.get("end_date"):
                duration = (booking["end_date"] - booking["start_date"]).days
                durations.append(duration)
        
        most_common_duration = Counter(durations).most_common(1)[0][0] if durations else 0
        
        return {
            "total_unique_customers": total_unique_customers,
            "repeat_customers": repeat_customers,
            "repeat_rate": round(repeat_rate, 1),
            "average_customer_spend": round(average_customer_spend, 2),
            "top_customers": top_customers,
            "customer_satisfaction_score": round(customer_satisfaction_score, 1),
            "customer_locations": customer_locations,
            "most_common_booking_duration": most_common_duration
        }
    
    except Exception as e:
        logger.error(f"Error getting customer analytics for user {user_id}: {str(e)}")
        return {}

async def get_owner_review_aggregation(user_id: str, request: Request) -> Dict[str, Any]:
    """Get aggregated review data for an owner"""
    try:
        database = request.app.mongodb
        
        # Get all reviews for this user as owner (received reviews)
        reviews = await database.reviews.find({
            "entity_type": "user",
            "entity_id": user_id
        }).sort("created_at", -1).to_list(None)
        
        if not reviews:
            return {
                "overall_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {},
                "cleanliness_rating": 0.0,
                "communication_rating": 0.0,
                "accuracy_rating": 0.0,
                "value_rating": 0.0,
                "recent_reviews": [],
                "rating_trend": "stable",
                "reviews_per_month": [],
                "positive_keywords": [],
                "improvement_areas": []
            }
        
        # Calculate overall rating
        overall_rating = sum(r.get("rating", 0) for r in reviews) / len(reviews)
        total_reviews = len(reviews)
        
        # Rating distribution
        from collections import Counter
        rating_counts = Counter(r.get("rating", 0) for r in reviews)
        rating_distribution = {str(k): v for k, v in rating_counts.items()}
        
        # Category ratings (if available in review data)
        category_ratings = {
            "cleanliness_rating": 0.0,
            "communication_rating": 0.0,
            "accuracy_rating": 0.0,
            "value_rating": 0.0
        }
        
        # For now, we'll estimate these based on overall rating and review content
        for category in category_ratings:
            category_ratings[category] = overall_rating  # Simplified
        
        # Recent reviews (last 5)
        recent_reviews = []
        for review in reviews[:5]:
            reviewer = await database.users.find_one({"_id": review.get("reviewer_id")})
            recent_reviews.append({
                "id": str(review.get("_id")),
                "rating": review.get("rating"),
                "title": review.get("title", ""),
                "content": review.get("content", ""),
                "reviewer_name": reviewer.get("full_name", "Anonymous") if reviewer else "Anonymous",
                "created_at": review.get("created_at")
            })
        
        # Rating trend analysis
        recent_reviews_ratings = [r.get("rating", 0) for r in reviews[:5]]
        older_reviews_ratings = [r.get("rating", 0) for r in reviews[5:15]] if len(reviews) > 5 else []
        
        recent_avg = sum(recent_reviews_ratings) / max(len(recent_reviews_ratings), 1)
        older_avg = sum(older_reviews_ratings) / max(len(older_reviews_ratings), 1)
        
        if recent_avg > older_avg + 0.2:
            rating_trend = "improving"
        elif recent_avg < older_avg - 0.2:
            rating_trend = "declining"
        else:
            rating_trend = "stable"
        
        # Reviews per month (last 12 months)
        reviews_per_month = []
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        now = datetime.utcnow()
        for i in range(12):
            month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = month_start + relativedelta(months=1)
            
            month_reviews = [r for r in reviews if month_start <= r.get("created_at", datetime.min) < month_end]
            reviews_per_month.append({
                "month": month_start.strftime("%Y-%m"),
                "count": len(month_reviews),
                "average_rating": sum(r.get("rating", 0) for r in month_reviews) / max(len(month_reviews), 1)
            })
        
        reviews_per_month.reverse()  # Chronological order
        
        # Extract keywords (simplified)
        positive_keywords = ["friendly", "clean", "responsive", "great", "excellent", "amazing", "professional"]
        improvement_areas = ["communication", "cleanliness", "accuracy", "timeliness", "flexibility"]
        
        return {
            "overall_rating": round(overall_rating, 1),
            "total_reviews": total_reviews,
            "rating_distribution": rating_distribution,
            "cleanliness_rating": round(category_ratings["cleanliness_rating"], 1),
            "communication_rating": round(category_ratings["communication_rating"], 1),
            "accuracy_rating": round(category_ratings["accuracy_rating"], 1),
            "value_rating": round(category_ratings["value_rating"], 1),
            "recent_reviews": recent_reviews,
            "rating_trend": rating_trend,
            "reviews_per_month": reviews_per_month,
            "positive_keywords": positive_keywords[:5],  # Top 5
            "improvement_areas": improvement_areas[:3]  # Top 3
        }
    
    except Exception as e:
        logger.error(f"Error getting review aggregation for user {user_id}: {str(e)}")
        return {} 