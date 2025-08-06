from typing import Optional, List, Dict, Any
from fastapi import Request
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import uuid
import calendar
import logging

logger = logging.getLogger(__name__)

async def get_user_earnings_breakdown(user_id: str, request: Request) -> Dict[str, Any]:
    """Get detailed earnings breakdown for a user"""
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Get all completed transactions for this user as owner
        completed_transactions = await database.transactions.find({
            "seller_id": user_id,
            "status": "completed",
            "type": "rental_payment"
        }).to_list(None)
        
        # Calculate total earnings
        total_earnings = sum(tx.get("amount", 0) for tx in completed_transactions)
        total_fees_paid = sum(tx.get("platform_fee", 0) for tx in completed_transactions)
        
        # Get current date info
        now = datetime.utcnow()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - relativedelta(months=1))
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate this month earnings
        this_month_earnings = sum(
            tx.get("amount", 0) for tx in completed_transactions 
            if tx.get("created_at", datetime.min) >= current_month_start
        )
        
        # Calculate last month earnings
        last_month_earnings = sum(
            tx.get("amount", 0) for tx in completed_transactions 
            if last_month_start <= tx.get("created_at", datetime.min) < current_month_start
        )
        
        # Calculate this year earnings
        this_year_earnings = sum(
            tx.get("amount", 0) for tx in completed_transactions 
            if tx.get("created_at", datetime.min) >= year_start
        )
        
        # Get user's current wallet balance
        user = await database.users.find_one({"_id": ObjectId(user_id)})
        current_balance = user.get("wallet_balance", 0.0) if user else 0.0
        
        # Get pending transactions (confirmed bookings not yet completed)
        pending_bookings = await database.bookings.find({
            "owner_id": user_id,
            "status": "confirmed",
            "end_date": {"$gte": datetime.utcnow()}
        }).to_list(None)
        
        pending_balance = sum(booking.get("total_amount", 0) * 0.85 for booking in pending_bookings)  # 85% after fees
        
        # Calculate available balance (current balance minus pending payouts)
        pending_payouts = await database.payouts.find({
            "user_id": user_id,
            "status": {"$in": ["pending", "processing"]}
        }).to_list(None)
        
        pending_payout_amount = sum(payout.get("amount", 0) for payout in pending_payouts)
        available_balance = max(0, current_balance - pending_payout_amount)
        
        # Get booking statistics
        total_bookings = await database.bookings.count_documents({
            "owner_id": user_id,
            "status": "completed"
        })
        
        average_booking_value = total_earnings / max(total_bookings, 1)
        
        # Count unique pets that have been rented
        rented_pets = await database.bookings.distinct("pet_id", {
            "owner_id": user_id,
            "status": "completed"
        })
        
        total_pets_rented = len(rented_pets)
        
        # Calculate average fee percentage
        average_fee_percentage = (total_fees_paid / max(total_earnings + total_fees_paid, 1)) * 100
        
        return {
            "total_earnings": total_earnings,
            "available_balance": available_balance,
            "pending_balance": pending_balance,
            "this_month_earnings": this_month_earnings,
            "last_month_earnings": last_month_earnings,
            "this_year_earnings": this_year_earnings,
            "rental_earnings": total_earnings,  # All earnings are from rentals for now
            "bonus_earnings": 0.0,  # Can be implemented later
            "referral_earnings": 0.0,  # Can be implemented later
            "total_fees_paid": total_fees_paid,
            "average_fee_percentage": average_fee_percentage,
            "total_bookings": total_bookings,
            "average_booking_value": average_booking_value,
            "total_pets_rented": total_pets_rented
        }
    
    except Exception as e:
        logger.error(f"Error getting earnings breakdown for user {user_id}: {str(e)}")
        return {}

async def get_monthly_earnings_breakdown(user_id: str, request: Request, months: int = 12) -> List[Dict[str, Any]]:
    """Get monthly earnings breakdown for specified number of months"""
    try:
        database = request.app.mongodb
        
        monthly_data = []
        now = datetime.utcnow()
        
        for i in range(months):
            month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = month_start + relativedelta(months=1)
            
            # Get transactions for this month
            transactions = await database.transactions.find({
                "seller_id": user_id,
                "status": "completed",
                "type": "rental_payment",
                "created_at": {"$gte": month_start, "$lt": month_end}
            }).to_list(None)
            
            total_earnings = sum(tx.get("amount", 0) for tx in transactions)
            total_bookings = len(transactions)
            fees_paid = sum(tx.get("platform_fee", 0) for tx in transactions)
            average_booking_value = total_earnings / max(total_bookings, 1)
            
            monthly_data.append({
                "month": month_start.strftime("%Y-%m"),
                "month_name": month_start.strftime("%B %Y"),
                "total_earnings": total_earnings,
                "total_bookings": total_bookings,
                "average_booking_value": average_booking_value,
                "fees_paid": fees_paid
            })
        
        return list(reversed(monthly_data))  # Most recent first
    
    except Exception as e:
        logger.error(f"Error getting monthly earnings for user {user_id}: {str(e)}")
        return []

async def get_detailed_wallet_info(user_id: str, request: Request) -> Dict[str, Any]:
    """Get detailed wallet information including recent transactions"""
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Get user info
        user = await database.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {}
        
        current_balance = user.get("wallet_balance", 0.0)
        
        # Get recent transactions (last 10)
        recent_transactions = await database.transactions.find({
            "$or": [
                {"buyer_id": user_id},
                {"seller_id": user_id}
            ]
        }).sort("created_at", -1).limit(10).to_list(None)
        
        # Format transactions
        formatted_transactions = []
        for tx in recent_transactions:
            tx_type = "credit" if tx.get("seller_id") == user_id else "debit"
            formatted_transactions.append({
                "id": str(tx.get("_id")),
                "type": tx_type,
                "amount": tx.get("amount", 0),
                "description": tx.get("description", ""),
                "date": tx.get("created_at"),
                "status": tx.get("status", "")
            })
        
        # Calculate totals
        total_earned = await database.transactions.aggregate([
            {"$match": {"seller_id": user_id, "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(None)
        
        total_withdrawn = await database.payouts.aggregate([
            {"$match": {"user_id": user_id, "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(None)
        
        total_earned_amount = total_earned[0]["total"] if total_earned else 0.0
        total_withdrawn_amount = total_withdrawn[0]["total"] if total_withdrawn else 0.0
        
        # Get pending balance
        pending_bookings = await database.bookings.find({
            "owner_id": user_id,
            "status": "confirmed",
            "end_date": {"$gte": datetime.utcnow()}
        }).to_list(None)
        
        pending_balance = sum(booking.get("total_amount", 0) * 0.85 for booking in pending_bookings)
        
        # Calculate available for withdrawal
        pending_payouts = await database.payouts.find({
            "user_id": user_id,
            "status": {"$in": ["pending", "processing"]}
        }).to_list(None)
        
        pending_payout_amount = sum(payout.get("amount", 0) for payout in pending_payouts)
        available_for_withdrawal = max(0, current_balance - pending_payout_amount)
        
        # Check verification status for payouts
        verification_required = not user.get("is_verified", False)
        
        return {
            "current_balance": current_balance,
            "available_for_withdrawal": available_for_withdrawal,
            "pending_balance": pending_balance,
            "total_earned": total_earned_amount,
            "total_withdrawn": total_withdrawn_amount,
            "currency": "USD",
            "recent_transactions": formatted_transactions,
            "minimum_payout": 20.0,
            "payout_methods": ["bank_transfer", "paypal"],
            "payout_enabled": True,
            "verification_required": verification_required
        }
    
    except Exception as e:
        logger.error(f"Error getting wallet info for user {user_id}: {str(e)}")
        return {}

async def create_payout_request(user_id: str, amount: float, method: str, account_details: Dict[str, Any], notes: str, request: Request) -> Optional[Dict[str, Any]]:
    """Create a new payout request"""
    try:
        database = request.app.mongodb
        from bson import ObjectId
        
        # Verify user has sufficient balance
        user = await database.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        
        current_balance = user.get("wallet_balance", 0.0)
        if current_balance < amount:
            return {"error": "Insufficient balance"}
        
        if amount < 20.0:  # Minimum payout amount
            return {"error": "Minimum payout amount is $20"}
        
        # Calculate processing fee (2.5% for most methods)
        processing_fee = amount * 0.025
        net_amount = amount - processing_fee
        
        # Create payout record
        payout_id = str(uuid.uuid4())
        payout_doc = {
            "_id": payout_id,
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "status": "pending",
            "account_details": account_details,
            "processing_fee": processing_fee,
            "net_amount": net_amount,
            "notes": notes,
            "requested_at": datetime.utcnow(),
            "processed_at": None,
            "completed_at": None,
            "failure_reason": None,
            "transaction_id": None
        }
        
        await database.payouts.insert_one(payout_doc)
        
        # Update user's wallet balance (deduct the amount)
        await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"wallet_balance": -amount}}
        )
        
        # Create transaction record
        transaction_doc = {
            "buyer_id": user_id,  # User is withdrawing money
            "seller_id": "platform",  # Platform is paying out
            "amount": amount,
            "type": "payout",
            "status": "pending",
            "description": f"Payout via {method}",
            "payout_id": payout_id,
            "created_at": datetime.utcnow()
        }
        
        await database.transactions.insert_one(transaction_doc)
        
        return {
            "id": payout_id,
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "status": "pending",
            "account_details": account_details,
            "processing_fee": processing_fee,
            "net_amount": net_amount,
            "notes": notes,
            "requested_at": datetime.utcnow(),
            "processed_at": None,
            "completed_at": None,
            "failure_reason": None,
            "transaction_id": None
        }
    
    except Exception as e:
        logger.error(f"Error creating payout request for user {user_id}: {str(e)}")
        return None

async def get_user_payouts(user_id: str, request: Request, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
    """Get user's payout history"""
    try:
        database = request.app.mongodb
        
        payouts = await database.payouts.find({
            "user_id": user_id
        }).sort("requested_at", -1).skip(skip).limit(limit).to_list(None)
        
        # Format payouts
        formatted_payouts = []
        for payout in payouts:
            formatted_payouts.append({
                "id": payout.get("_id"),
                "user_id": payout.get("user_id"),
                "amount": payout.get("amount"),
                "method": payout.get("method"),
                "status": payout.get("status"),
                "account_details": payout.get("account_details", {}),
                "processing_fee": payout.get("processing_fee"),
                "net_amount": payout.get("net_amount"),
                "notes": payout.get("notes"),
                "requested_at": payout.get("requested_at"),
                "processed_at": payout.get("processed_at"),
                "completed_at": payout.get("completed_at"),
                "failure_reason": payout.get("failure_reason"),
                "transaction_id": payout.get("transaction_id")
            })
        
        return formatted_payouts
    
    except Exception as e:
        logger.error(f"Error getting payouts for user {user_id}: {str(e)}")
        return []

async def get_top_performing_pets(user_id: str, request: Request, limit: int = 5) -> List[Dict[str, Any]]:
    """Get top performing pets by earnings for a user"""
    try:
        database = request.app.mongodb
        
        # Aggregate earnings by pet
        pipeline = [
            {"$match": {"owner_id": user_id, "status": "completed"}},
            {"$group": {
                "_id": "$pet_id",
                "total_earnings": {"$sum": "$total_amount"},
                "total_bookings": {"$sum": 1},
                "average_booking_value": {"$avg": "$total_amount"}
            }},
            {"$sort": {"total_earnings": -1}},
            {"$limit": limit}
        ]
        
        pet_stats = await database.bookings.aggregate(pipeline).to_list(None)
        
        # Get pet details
        top_pets = []
        for stats in pet_stats:
            pet = await database.pets.find_one({"_id": stats["_id"]})
            if pet:
                # Get reviews for this pet
                reviews = await database.reviews.find({
                    "entity_id": stats["_id"],
                    "entity_type": "pet"
                }).to_list(None)
                
                average_rating = sum(r.get("rating", 0) for r in reviews) / max(len(reviews), 1)
                
                top_pets.append({
                    "id": str(stats["_id"]),
                    "name": pet.get("name"),
                    "type": pet.get("type"),
                    "total_bookings": stats["total_bookings"],
                    "total_earnings": stats["total_earnings"] * 0.85,  # After platform fees
                    "average_booking_value": stats["average_booking_value"],
                    "rating": round(average_rating, 1),
                    "total_reviews": len(reviews)
                })
        
        return top_pets
    
    except Exception as e:
        logger.error(f"Error getting top performing pets for user {user_id}: {str(e)}")
        return [] 