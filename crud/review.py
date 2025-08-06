from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bson import ObjectId
from fastapi import Request

from schemas.review import ReviewType


async def create_review(
    entity_id: str,
    entity_type: ReviewType,
    review_data: Dict[str, Any],
    reviewer_id: str,
    reviewer_name: str,
    reviewer_avatar: Optional[str],
    transaction_id: Optional[str] = None,
    request: Request = None
) -> Dict[str, Any]:
    """
    Create a new review
    """
    database = request.app.mongodb
    
    # Check if entity exists
    if entity_type == ReviewType.USER:
        entity = await database.users.find_one({"_id": ObjectId(entity_id)})
    else:  # entity_type == ReviewType.PET
        entity = await database.pets.find_one({"_id": ObjectId(entity_id)})
    
    if not entity:
        return None
    
    # Check if user has already reviewed this entity
    existing_review = await database.reviews.find_one({
        "reviewer_id": reviewer_id,
        "entity_id": entity_id,
        "entity_type": entity_type
    })
    
    if existing_review:
        # If transaction_id is provided, update existing review to link to transaction
        if transaction_id and not existing_review.get("transaction_id"):
            await database.reviews.update_one(
                {"_id": existing_review["_id"]},
                {"$set": {"transaction_id": transaction_id}}
            )
        
        return None  # User already reviewed this entity
    
    # Create review
    now = datetime.utcnow()
    review = {
        "reviewer_id": reviewer_id,
        "reviewer_name": reviewer_name,
        "reviewer_avatar": reviewer_avatar,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "rating": review_data.get("rating"),
        "title": review_data.get("title"),
        "comment": review_data.get("comment"),
        "attributes": review_data.get("attributes", {}),
        "images": review_data.get("images", []),
        "anonymous": review_data.get("anonymous", False),
        "transaction_id": transaction_id,
        "created_at": now,
        "updated_at": now,
        "helpful_count": 0,
        "helpful_users": [],
        "reported": False,
        "report_count": 0,
        "report_reasons": [],
        "deleted": False
    }
    
    result = await database.reviews.insert_one(review)
    
    if not result.inserted_id:
        return None
        
    review["id"] = str(result.inserted_id)
    
    # Update entity's reviews stats
    if entity_type == ReviewType.USER:
        await update_user_review_stats(entity_id, database)
    else:  # entity_type == ReviewType.PET
        await update_pet_review_stats(entity_id, database)
    
    # Create notification for review recipient
    if entity_type == ReviewType.USER:
        recipient_id = entity_id
    else:  # Pet review - send notification to owner
        recipient_id = entity.get("owner_id")
        
    if recipient_id and recipient_id != reviewer_id:
        try:
            from crud.notification import create_notification
            from schemas.notification import NotificationType
            
            # Create notification data
            notification_data = {
                "recipient_id": recipient_id,
                "type": NotificationType.REVIEW_RECEIVED,
                "title": "New Review Received",
                "message": f"You received a new {entity_type} review with a rating of {review_data.get('rating')} stars.",
                "related_entity_id": entity_id,
                "related_entity_type": entity_type,
                "data": {
                    "review_id": str(result.inserted_id),
                    "rating": review_data.get("rating")
                }
            }
            
            await create_notification(notification_data, request)
        except Exception as e:
            # Log the error but don't fail the review creation
            print(f"Failed to create notification: {str(e)}")
    
    return review


async def update_review(
    review_id: str,
    update_data: Dict[str, Any],
    user_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Update a review
    """
    database = request.app.mongodb
    
    # Check if review exists and belongs to user
    review = await database.reviews.find_one({
        "_id": ObjectId(review_id),
        "reviewer_id": user_id,
        "deleted": {"$ne": True}
    })
    
    if not review:
        return None
    
    # Prepare update data
    update_dict = {}
    
    if "rating" in update_data:
        update_dict["rating"] = update_data["rating"]
        
    if "title" in update_data:
        update_dict["title"] = update_data["title"]
        
    if "comment" in update_data:
        update_dict["comment"] = update_data["comment"]
        
    if "attributes" in update_data:
        update_dict["attributes"] = update_data["attributes"]
    
    if not update_dict:
        # Nothing to update
        return await get_review_by_id(review_id, request)
    
    # Add updated_at timestamp
    update_dict["updated_at"] = datetime.utcnow()
    
    # Update review
    result = await database.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        return None
    
    # Update entity's reviews stats
    entity_id = review["entity_id"]
    entity_type = review["entity_type"]
    
    if entity_type == ReviewType.USER:
        await update_user_review_stats(entity_id, database)
    else:  # entity_type == ReviewType.PET
        await update_pet_review_stats(entity_id, database)
    
    # Return updated review
    return await get_review_by_id(review_id, request)


async def delete_review(
    review_id: str,
    user_id: str,
    request: Request
) -> bool:
    """
    Delete a review (soft delete)
    """
    database = request.app.mongodb
    
    # Check if review exists and belongs to user
    review = await database.reviews.find_one({
        "_id": ObjectId(review_id),
        "reviewer_id": user_id,
        "deleted": {"$ne": True}
    })
    
    if not review:
        return False
    
    # Soft delete review
    result = await database.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {"deleted": True, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        return False
    
    # Update entity's reviews stats
    entity_id = review["entity_id"]
    entity_type = review["entity_type"]
    
    if entity_type == ReviewType.USER:
        await update_user_review_stats(entity_id, database)
    else:  # entity_type == ReviewType.PET
        await update_pet_review_stats(entity_id, database)
    
    return True


async def get_review_by_id(
    review_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Get a review by ID
    """
    database = request.app.mongodb
    
    review = await database.reviews.find_one({
        "_id": ObjectId(review_id),
        "deleted": {"$ne": True}
    })
    
    if review:
        review["id"] = str(review.pop("_id"))
        return review
        
    return None


async def get_entity_reviews(
    entity_id: str,
    entity_type: ReviewType,
    skip: int = 0,
    limit: int = 20,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    request: Request = None
) -> List[Dict[str, Any]]:
    """
    Get all reviews for an entity with filtering and sorting
    """
    database = request.app.mongodb
    
    # Build query
    query = {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "deleted": {"$ne": True}
    }
    
    # Add rating filters if provided
    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}
        
    if max_rating is not None:
        if "rating" in query:
            query["rating"]["$lte"] = max_rating
        else:
            query["rating"] = {"$lte": max_rating}
    
    # Determine sort direction
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    
    # Get reviews
    cursor = database.reviews.find(query)
    
    # Sort reviews
    cursor = cursor.sort(sort_by, sort_direction)
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(limit)
    
    # Convert to list
    reviews = []
    async for review in cursor:
        review["id"] = str(review.pop("_id"))
        
        # Remove internal fields
        review.pop("helpful_users", None)
        review.pop("report_reasons", None)
        
        reviews.append(review)
    
    return reviews


async def get_user_reviews(
    user_id: str,
    as_reviewer: bool = True,
    skip: int = 0,
    limit: int = 20,
    request: Request = None
) -> List[Dict[str, Any]]:
    """
    Get all reviews by a user (as_reviewer=True) or for a user (as_reviewer=False)
    """
    database = request.app.mongodb
    
    # Build query
    if as_reviewer:
        query = {"reviewer_id": user_id, "deleted": {"$ne": True}}
    else:
        query = {"entity_id": user_id, "entity_type": ReviewType.USER, "deleted": {"$ne": True}}
    
    # Get reviews
    cursor = database.reviews.find(query)
    
    # Sort by created_at in descending order (newest first)
    cursor = cursor.sort("created_at", -1)
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(limit)
    
    # Convert to list
    reviews = []
    async for review in cursor:
        review["id"] = str(review.pop("_id"))
        
        # Remove internal fields
        review.pop("helpful_users", None)
        review.pop("report_reasons", None)
        
        reviews.append(review)
    
    return reviews


async def get_reviews_summary(
    entity_id: str,
    entity_type: ReviewType,
    request: Request
) -> Dict[str, Any]:
    """
    Get a summary of reviews for an entity
    """
    database = request.app.mongodb
    
    # Count total reviews
    count = await database.reviews.count_documents({
        "entity_id": entity_id,
        "entity_type": entity_type,
        "deleted": {"$ne": True}
    })
    
    if count == 0:
        return {
            "count": 0,
            "average_rating": 0.0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "attributes_avg": {}
        }
    
    # Get rating distribution
    pipeline = [
        {
            "$match": {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "deleted": {"$ne": True}
            }
        },
        {
            "$group": {
                "_id": "$rating",
                "count": {"$sum": 1}
            }
        }
    ]
    
    cursor = database.reviews.aggregate(pipeline)
    rating_distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    
    async for doc in cursor:
        rating = str(doc["_id"])
        rating_distribution[rating] = doc["count"]
    
    # Calculate average rating
    total_rating = sum(int(rating) * count for rating, count in rating_distribution.items())
    average_rating = total_rating / count if count > 0 else 0
    
    # Get average attributes if any reviews have attributes
    attributes_avg = {}
    has_attributes = await database.reviews.find_one({
        "entity_id": entity_id,
        "entity_type": entity_type,
        "attributes": {"$exists": True, "$ne": {}},
        "deleted": {"$ne": True}
    })
    
    if has_attributes:
        # Find all attribute keys first
        attribute_keys = set()
        cursor = database.reviews.find({
            "entity_id": entity_id,
            "entity_type": entity_type,
            "attributes": {"$exists": True, "$ne": {}},
            "deleted": {"$ne": True}
        })
        
        async for review in cursor:
            attribute_keys.update(review.get("attributes", {}).keys())
        
        # Calculate average for each attribute
        for attr_key in attribute_keys:
            pipeline = [
                {
                    "$match": {
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                        f"attributes.{attr_key}": {"$exists": True},
                        "deleted": {"$ne": True}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "average": {"$avg": f"$attributes.{attr_key}"},
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            result = await database.reviews.aggregate(pipeline).to_list(length=1)
            if result:
                attributes_avg[attr_key] = {
                    "average": round(result[0]["average"], 1),
                    "count": result[0]["count"]
                }
    
    return {
        "count": count,
        "average_rating": round(average_rating, 1),
        "rating_distribution": rating_distribution,
        "attributes_avg": attributes_avg
    }


async def mark_review_helpful(
    review_id: str,
    user_id: str,
    helpful: bool,
    request: Request
) -> bool:
    """
    Mark a review as helpful or unhelpful
    """
    database = request.app.mongodb
    
    # Check if review exists
    review = await database.reviews.find_one({
        "_id": ObjectId(review_id),
        "deleted": {"$ne": True}
    })
    
    if not review:
        return False
    
    # Check if user is the reviewer (can't mark own reviews)
    if review.get("reviewer_id") == user_id:
        return False
    
    helpful_users = review.get("helpful_users", [])
    
    # Check if user already marked this review
    if user_id in helpful_users and helpful:
        # User already marked it as helpful
        return True
    elif user_id not in helpful_users and not helpful:
        # User already unmarked or never marked
        return True
    
    # Update review
    if helpful:
        # Add user to helpful_users and increment count
        result = await database.reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$addToSet": {"helpful_users": user_id}, "$inc": {"helpful_count": 1}}
        )
    else:
        # Remove user from helpful_users and decrement count
        result = await database.reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$pull": {"helpful_users": user_id}, "$inc": {"helpful_count": -1}}
        )
    
    return result.modified_count > 0


async def report_review(
    review_id: str,
    user_id: str,
    reason: str,
    details: Optional[str],
    request: Request
) -> bool:
    """
    Report a review for inappropriate content
    """
    database = request.app.mongodb
    
    # Check if review exists
    review = await database.reviews.find_one({
        "_id": ObjectId(review_id),
        "deleted": {"$ne": True}
    })
    
    if not review:
        return False
    
    # Check if user is the reviewer (can't report own reviews)
    if review.get("reviewer_id") == user_id:
        return False
    
    # Check if report already exists
    report_reasons = review.get("report_reasons", [])
    for report in report_reasons:
        if report.get("user_id") == user_id:
            # User already reported this review
            return True
    
    # Create report
    report = {
        "user_id": user_id,
        "reason": reason,
        "details": details,
        "reported_at": datetime.utcnow()
    }
    
    # Add report to review
    result = await database.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {
            "$push": {"report_reasons": report},
            "$inc": {"report_count": 1},
            "$set": {"reported": True}
        }
    )
    
    if result.modified_count > 0:
        # Create a report document for admin review
        await database.reports.insert_one({
            "type": "review",
            "entity_id": review_id,
            "reporter_id": user_id,
            "reason": reason,
            "details": details,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "entity_data": {
                "review_text": review.get("comment", ""),
                "review_rating": review.get("rating", 0),
                "reviewer_id": review.get("reviewer_id", "")
            }
        })
        
        return True
    
    return False


async def get_pending_review_opportunities(
    user_id: str,
    request: Request
) -> List[Dict[str, Any]]:
    """
    Get a list of completed transactions that the user can review
    """
    database = request.app.mongodb
    
    # Find completed transactions where user was a buyer or seller
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"buyer_id": user_id},
                    {"seller_id": user_id}
                ],
                "status": "completed",
                "completed_at": {"$exists": True}
            }
        },
        {
            # Look up if the user has already reviewed the other party
            "$lookup": {
                "from": "reviews",
                "let": {
                    "buyer_id": "$buyer_id",
                    "seller_id": "$seller_id",
                    "transaction_id": "$_id"
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$reviewer_id", user_id]},
                                    {"$eq": ["$entity_type", ReviewType.USER]},
                                    {
                                        "$or": [
                                            {
                                                "$and": [
                                                    {"$eq": ["$reviewer_id", "$$buyer_id"]},
                                                    {"$eq": ["$entity_id", "$$seller_id"]}
                                                ]
                                            },
                                            {
                                                "$and": [
                                                    {"$eq": ["$reviewer_id", "$$seller_id"]},
                                                    {"$eq": ["$entity_id", "$$buyer_id"]}
                                                ]
                                            }
                                        ]
                                    },
                                    {"$eq": ["$transaction_id", {"$toString": "$$transaction_id"}]}
                                ]
                            }
                        }
                    }
                ],
                "as": "user_reviews"
            }
        },
        {
            # Look up if the user has already reviewed the pet
            "$lookup": {
                "from": "reviews",
                "let": {
                    "pet_id": "$pet_id",
                    "transaction_id": "$_id"
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$reviewer_id", user_id]},
                                    {"$eq": ["$entity_type", ReviewType.PET]},
                                    {"$eq": ["$entity_id", "$$pet_id"]},
                                    {"$eq": ["$transaction_id", {"$toString": "$$transaction_id"}]}
                                ]
                            }
                        }
                    }
                ],
                "as": "pet_reviews"
            }
        },
        {
            # Look up pet details
            "$lookup": {
                "from": "pets",
                "let": {"pet_id": "$pet_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$_id", {"$toObjectId": "$$pet_id"}]}
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "name": 1,
                            "type": 1,
                            "breed": 1,
                            "owner_id": 1,
                            "photos": {"$slice": ["$photos", 1]}
                        }
                    }
                ],
                "as": "pet_info"
            }
        },
        {
            # Look up other user details
            "$lookup": {
                "from": "users",
                "let": {
                    "buyer_id": "$buyer_id",
                    "seller_id": "$seller_id"
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$or": [
                                    {"$and": [
                                        {"$eq": ["$_id", {"$toObjectId": "$$buyer_id"}]},
                                        {"$ne": ["$$buyer_id", user_id]}
                                    ]},
                                    {"$and": [
                                        {"$eq": ["$_id", {"$toObjectId": "$$seller_id"}]},
                                        {"$ne": ["$$seller_id", user_id]}
                                    ]}
                                ]
                            }
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "name": 1,
                            "avatar_url": 1
                        }
                    }
                ],
                "as": "other_user_info"
            }
        },
        {
            "$project": {
                "_id": 1,
                "pet_id": 1,
                "buyer_id": 1,
                "seller_id": 1,
                "status": 1,
                "completed_at": 1,
                "has_user_review": {"$gt": [{"$size": "$user_reviews"}, 0]},
                "has_pet_review": {"$gt": [{"$size": "$pet_reviews"}, 0]},
                "pet_info": {"$arrayElemAt": ["$pet_info", 0]},
                "other_user_info": {"$arrayElemAt": ["$other_user_info", 0]}
            }
        },
        {
            "$match": {
                "$or": [
                    {"has_user_review": False},
                    {"has_pet_review": False}
                ]
            }
        },
        {
            "$sort": {"completed_at": -1}
        }
    ]
    
    results = await database.transactions.aggregate(pipeline).to_list(length=100)
    
    opportunities = []
    for result in results:
        result["id"] = str(result.pop("_id"))
        
        # Clean up the data
        pet_info = result.pop("pet_info", {}) or {}
        if pet_info:
            pet_info["id"] = str(pet_info.pop("_id")) if "_id" in pet_info else None
            
        other_user_info = result.pop("other_user_info", {}) or {}
        if other_user_info:
            other_user_info["id"] = str(other_user_info.pop("_id")) if "_id" in other_user_info else None
            
        # Determine who the other user is
        if result["buyer_id"] == user_id:
            other_user_id = result["seller_id"]
            user_role = "buyer"
        else:
            other_user_id = result["buyer_id"]
            user_role = "seller"
            
        # Create opportunity object
        opportunity = {
            "transaction_id": result["id"],
            "completed_at": result["completed_at"],
            "user_role": user_role,
            "can_review_user": not result["has_user_review"],
            "can_review_pet": not result["has_pet_review"] and user_role == "buyer",
            "pet": pet_info,
            "other_user": other_user_info
        }
        
        opportunities.append(opportunity)
    
    return opportunities


async def update_user_review_stats(user_id: str, database) -> None:
    """
    Update user's review stats
    """
    # Calculate review summary
    summary = await get_reviews_summary_from_database(user_id, ReviewType.USER, database)
    
    # Update user document
    await database.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "rating": summary["average_rating"],
            "review_count": summary["count"],
            "review_summary": summary
        }}
    )


async def update_pet_review_stats(pet_id: str, database) -> None:
    """
    Update pet's review stats
    """
    # Calculate review summary
    summary = await get_reviews_summary_from_database(pet_id, ReviewType.PET, database)
    
    # Update pet document
    await database.pets.update_one(
        {"_id": ObjectId(pet_id)},
        {"$set": {
            "rating": summary["average_rating"],
            "review_count": summary["count"],
            "review_summary": summary
        }}
    )


async def get_reviews_summary_from_database(
    entity_id: str,
    entity_type: ReviewType,
    database
) -> Dict[str, Any]:
    """
    Get a summary of reviews for an entity directly from database
    """
    # Count total reviews
    count = await database.reviews.count_documents({
        "entity_id": entity_id,
        "entity_type": entity_type,
        "deleted": {"$ne": True}
    })
    
    if count == 0:
        return {
            "count": 0,
            "average_rating": 0.0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "attributes_avg": {}
        }
    
    # Get rating distribution
    pipeline = [
        {
            "$match": {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "deleted": {"$ne": True}
            }
        },
        {
            "$group": {
                "_id": "$rating",
                "count": {"$sum": 1}
            }
        }
    ]
    
    cursor = database.reviews.aggregate(pipeline)
    rating_distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    
    async for doc in cursor:
        rating = str(doc["_id"])
        rating_distribution[rating] = doc["count"]
    
    # Calculate average rating
    total_rating = sum(int(rating) * count for rating, count in rating_distribution.items())
    average_rating = total_rating / count if count > 0 else 0
    
    # Get average attributes if any reviews have attributes
    attributes_avg = {}
    has_attributes = await database.reviews.find_one({
        "entity_id": entity_id,
        "entity_type": entity_type,
        "attributes": {"$exists": True, "$ne": {}},
        "deleted": {"$ne": True}
    })
    
    if has_attributes:
        # Find all attribute keys first
        attribute_keys = set()
        cursor = database.reviews.find({
            "entity_id": entity_id,
            "entity_type": entity_type,
            "attributes": {"$exists": True, "$ne": {}},
            "deleted": {"$ne": True}
        })
        
        async for review in cursor:
            attribute_keys.update(review.get("attributes", {}).keys())
        
        # Calculate average for each attribute
        for attr_key in attribute_keys:
            pipeline = [
                {
                    "$match": {
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                        f"attributes.{attr_key}": {"$exists": True},
                        "deleted": {"$ne": True}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "average": {"$avg": f"$attributes.{attr_key}"},
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            result = await database.reviews.aggregate(pipeline).to_list(length=1)
            if result:
                attributes_avg[attr_key] = {
                    "average": round(result[0]["average"], 1),
                    "count": result[0]["count"]
                }
    
    return {
        "count": count,
        "average_rating": round(average_rating, 1),
        "rating_distribution": rating_distribution,
        "attributes_avg": attributes_avg
    } 