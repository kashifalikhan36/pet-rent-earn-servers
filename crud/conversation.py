from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from fastapi import Request
from schemas.conversation import ConversationCreate, MessageCreate
from bson.objectid import ObjectId


async def create_conversation(
    data: ConversationCreate,
    sender_id: str,
    request: Request
) -> Optional[Dict[str, Any]]:
    """Create a new conversation with initial message."""
    try:
        database = request.app.mongodb
        
        # Check if recipient exists
        recipient = await database.users.find_one({"_id": ObjectId(data.recipient_id)})
        if not recipient:
            return None
            
        # Check if there's already a conversation between these users
        existing_conversation = await database.conversations.find_one({
            "participants": {"$all": [sender_id, data.recipient_id]}
        })
        
        if existing_conversation:
            # Add new message to existing conversation
            now = datetime.utcnow()
            conversation_id = str(existing_conversation["_id"])
            message = {
                "id": str(ObjectId()),
                "conversation_id": conversation_id,  # Add this field
                "sender_id": sender_id,
                "content": data.message,
                "read": False,
                "attachment_urls": data.attachment_urls,
                "created_at": now
            }
            
            await database.conversations.update_one(
                {"_id": existing_conversation["_id"]},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": now, "last_message": message}
                }
            )
            
            # Get updated conversation
            conversation = await database.conversations.find_one({"_id": existing_conversation["_id"]})
            conversation["id"] = str(conversation["_id"])
            del conversation["_id"]
            
            # Add participant details
            await _add_participant_details(conversation, database)
            
            return conversation
        
        # Create new conversation
        now = datetime.utcnow()
        conversation_doc = {
            "participants": [sender_id, data.recipient_id],
            "created_at": now,
            "updated_at": now
        }
        
        if data.related_pet_id:
            conversation_doc["related_pet_id"] = data.related_pet_id
            
        if data.related_booking_id:
            conversation_doc["related_booking_id"] = data.related_booking_id
        
        # Insert conversation
        result = await database.conversations.insert_one(conversation_doc)
        conversation_id = str(result.inserted_id)
        
        # Add initial message
        message = {
            "id": str(ObjectId()),
            "conversation_id": conversation_id,  # Add this field
            "sender_id": sender_id,
            "content": data.message,
            "read": False,
            "attachment_urls": data.attachment_urls,
            "created_at": now
        }
        
        # Update conversation with message
        await database.conversations.update_one(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "messages": [message],
                    "last_message": message
                }
            }
        )
        
        # Get created conversation
        conversation = await database.conversations.find_one({"_id": result.inserted_id})
        if conversation:
            conversation["id"] = str(conversation["_id"])
            del conversation["_id"]
            
            # Add participant details
            await _add_participant_details(conversation, database)
            
        return conversation
        
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None


async def get_conversation(conversation_id: str, user_id: str, request: Request) -> Optional[Dict[str, Any]]:
    """Get conversation by ID (only if user is participant)."""
    try:
        database = request.app.mongodb
        
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if conversation:
            conversation["id"] = str(conversation["_id"])
            del conversation["_id"]
            
            # Ensure all messages have conversation_id
            if "messages" in conversation:
                for message in conversation["messages"]:
                    if "conversation_id" not in message:
                        message["conversation_id"] = conversation["id"]
            
            # Add participant details
            await _add_participant_details(conversation, database)
            
            # Calculate unread count for current user
            unread_count = 0
            for message in conversation.get("messages", []):
                if message["sender_id"] != user_id and not message.get("read"):
                    unread_count += 1
                    
            conversation["unread_count"] = unread_count
            
            # Mark all messages as read
            await database.conversations.update_many(
                {"_id": ObjectId(conversation_id), "messages.sender_id": {"$ne": user_id}},
                {"$set": {"messages.$[elem].read": True}},
                array_filters=[{"elem.sender_id": {"$ne": user_id}, "elem.read": False}]
            )
            
        return conversation
        
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return None


async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    sender_id: str,
    request: Request
) -> Optional[Dict[str, Any]]:
    """Send a new message in an existing conversation."""
    try:
        database = request.app.mongodb
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": sender_id
        })
        
        if not conversation:
            return None
            
        # Create message
        now = datetime.utcnow()
        message = {
            "id": str(ObjectId()),
            "conversation_id": conversation_id,  # Add this field
            "sender_id": sender_id,
            "content": message_data.content,
            "read": False,
            "attachment_urls": message_data.attachment_urls,
            "created_at": now
        }
        
        # Add message to conversation
        await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": now, "last_message": message}
            }
        )
        
        return message
        
    except Exception as e:
        print(f"Error sending message: {e}")
        return None


async def get_user_conversations(
    user_id: str,
    request: Request,
    page: int = 1,
    limit: int = 20,
    archived: bool = False
) -> Tuple[List[Dict[str, Any]], int]:
    """Get user's conversations with pagination."""
    try:
        database = request.app.mongodb
        skip = (page - 1) * limit
        
        query = {"participants": user_id}
        
        # Filter by archived status if requested
        if archived:
            query["archived_by"] = user_id
        else:
            query["$or"] = [
                {"archived_by": {"$exists": False}},
                {"archived_by": {"$ne": user_id}}
            ]
        
        # Count total conversations
        total = await database.conversations.count_documents(query)
        
        # Get conversations with pagination
        conversations = []
        async for conversation in database.conversations.find(query).sort("updated_at", -1).skip(skip).limit(limit):
            conversation_id = str(conversation["_id"])
            conversation["id"] = conversation_id
            del conversation["_id"]
            
            # Ensure all messages have conversation_id
            if "messages" in conversation:
                for message in conversation["messages"]:
                    if "conversation_id" not in message:
                        message["conversation_id"] = conversation_id
            
            # Find the other participant
            other_participant_id = next((p for p in conversation["participants"] if p != user_id), None)
            
            # Get other participant details
            if other_participant_id:
                other_participant = await database.users.find_one({"_id": ObjectId(other_participant_id)})
                if other_participant:
                    conversation["other_participant_id"] = other_participant_id
                    conversation["other_participant_name"] = other_participant["name"]
                    conversation["other_participant_avatar"] = other_participant.get("avatar_url")
            
            # Calculate unread count
            unread_count = 0
            for message in conversation.get("messages", []):
                if message["sender_id"] != user_id and not message.get("read"):
                    unread_count += 1
                    
            conversation["unread_count"] = unread_count
            
            # Get last message
            last_message = conversation.get("last_message", {})
            if last_message:
                if "conversation_id" not in last_message:
                    last_message["conversation_id"] = conversation_id
                conversation["last_message_text"] = last_message.get("content", "")
                conversation["last_message_time"] = last_message.get("created_at", conversation.get("updated_at"))
            
            conversations.append(conversation)
            
        return conversations, total
        
    except Exception as e:
        print(f"Error getting user conversations: {e}")
        return [], 0


async def _add_participant_details(conversation: Dict[str, Any], database) -> None:
    """Add participant details to conversation."""
    participant_details = {}
    
    for participant_id in conversation.get("participants", []):
        participant = await database.users.find_one({"_id": ObjectId(participant_id)})
        if participant:
            participant_details[participant_id] = {
                "id": participant_id,
                "name": participant["name"],
                "avatar_url": participant.get("avatar_url")
            }
            
    conversation["participant_details"] = participant_details 


async def mark_conversation_as_read(
    conversation_id: str,
    user_id: str,
    request: Request
) -> bool:
    """Mark all messages in a conversation as read."""
    try:
        database = request.app.mongodb
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if not conversation:
            return False
        
        # Mark all messages from other participants as read
        result = await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"messages.$[elem].read": True}},
            array_filters=[{"elem.sender_id": {"$ne": user_id}, "elem.read": False}]
        )
        
        return result.modified_count > 0 or result.matched_count > 0
        
    except Exception as e:
        print(f"Error marking conversation as read: {e}")
        return False


async def delete_message(
    conversation_id: str,
    message_id: str,
    user_id: str,
    request: Request
) -> bool:
    """Delete a message (only sender can delete)."""
    try:
        database = request.app.mongodb
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id,
            "messages": {"$elemMatch": {"id": message_id, "sender_id": user_id}}
        })
        
        if not conversation:
            return False
        
        # Remove the message from the conversation
        result = await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$pull": {"messages": {"id": message_id}}}
        )
        
        # If the deleted message was the last message, update the last_message field
        if conversation.get("last_message", {}).get("id") == message_id:
            # Find the new last message
            updated_conversation = await database.conversations.find_one({"_id": ObjectId(conversation_id)})
            if updated_conversation and updated_conversation.get("messages"):
                messages = updated_conversation["messages"]
                if messages:
                    # Sort by created_at in descending order
                    messages.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
                    new_last_message = messages[0]
                    
                    # Update the last_message
                    await database.conversations.update_one(
                        {"_id": ObjectId(conversation_id)},
                        {"$set": {"last_message": new_last_message}}
                    )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error deleting message: {e}")
        return False


async def send_image_message(
    conversation_id: str,
    user_id: str,
    files: List[object],  # List of UploadFile objects
    request: Request
) -> Optional[Dict[str, Any]]:
    """Send image messages in a conversation."""
    try:
        database = request.app.mongodb
        from utils.file_upload import upload_image_file
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if not conversation:
            return None
        
        # Upload images
        image_urls = []
        for file in files:
            # Upload each image to the conversation_images directory
            image_url = await upload_image_file(file, "conversation_images")
            if image_url:
                image_urls.append(image_url)
        
        if not image_urls:
            return None
        
        # Create message with images
        now = datetime.utcnow()
        message = {
            "id": str(ObjectId()),
            "conversation_id": conversation_id,
            "sender_id": user_id,
            "content": "",  # Empty content for image-only messages
            "read": False,
            "attachment_urls": image_urls,
            "is_image_message": True,
            "created_at": now
        }
        
        # Add message to conversation
        await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": now, "last_message": message}
            }
        )
        
        return message
        
    except Exception as e:
        print(f"Error sending image message: {e}")
        return None


async def archive_conversation(
    conversation_id: str,
    user_id: str,
    archive: bool,
    request: Request
) -> bool:
    """Archive or unarchive a conversation."""
    try:
        database = request.app.mongodb
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if not conversation:
            return False
        
        # Archive/unarchive the conversation for this user
        # We use a separate array to track which users have archived the conversation
        operation = "$addToSet" if archive else "$pull"
        
        result = await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {operation: {"archived_by": user_id}}
        )
        
        return result.modified_count > 0 or result.matched_count > 0
        
    except Exception as e:
        print(f"Error archiving conversation: {e}")
        return False 


async def create_conversation_offer(
    conversation_id: str,
    offer_data: Dict[str, Any],
    sender_id: str,
    request: Request
) -> Optional[Dict[str, Any]]:
    """Create a new offer in a conversation."""
    try:
        database = request.app.mongodb
        from schemas.conversation import OfferStatus
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": sender_id
        })
        
        if not conversation:
            return None
            
        # Get pet details to include in the offer
        pet = None
        if "pet_id" in offer_data:
            pet = await database.pets.find_one({"_id": ObjectId(offer_data["pet_id"])})
            if not pet:
                return None
                
            # Make sure pet ID is stored as string
            offer_data["pet_id"] = str(pet["_id"])
            
        # Get sender details
        sender = await database.users.find_one({"_id": ObjectId(sender_id)})
        
        # Create offer document
        now = datetime.utcnow()
        expires_at = now + datetime.timedelta(hours=offer_data.get("expire_after_hours", 24))
        
        offer_id = str(ObjectId())
        offer = {
            "id": offer_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "status": OfferStatus.PENDING,
            "created_at": now,
            "expires_at": expires_at,
            "responded_at": None,
            **offer_data
        }
        
        # Remove expire_after_hours from the final offer
        if "expire_after_hours" in offer:
            del offer["expire_after_hours"]
        
        # Save the offer
        await database.conversation_offers.insert_one({
            "_id": ObjectId(offer_id),
            **offer
        })
        
        # Create a message in the conversation about the offer
        message = {
            "id": str(ObjectId()),
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "content": f"New offer: ${offer_data.get('price', 0):.2f}",
            "read": False,
            "is_offer": True,
            "offer_id": offer_id,
            "created_at": now
        }
        
        # Add message to conversation
        await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": now, "last_message": message}
            }
        )
        
        # Add pet and sender details to response
        if pet:
            offer["pet_details"] = {
                "id": str(pet["_id"]),
                "name": pet.get("name", ""),
                "type": pet.get("type", ""),
                "photos": pet.get("photos", [])
            }
            
        if sender:
            offer["sender_details"] = {
                "id": sender_id,
                "name": sender.get("name", ""),
                "avatar_url": sender.get("avatar_url")
            }
            
        return offer
        
    except Exception as e:
        print(f"Error creating conversation offer: {e}")
        return None


async def get_conversation_offers(
    conversation_id: str,
    user_id: str,
    request: Request
) -> List[Dict[str, Any]]:
    """Get all offers in a conversation."""
    try:
        database = request.app.mongodb
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if not conversation:
            return []
            
        # Get offers
        offers = []
        cursor = database.conversation_offers.find({
            "conversation_id": conversation_id
        }).sort("created_at", -1)
        
        async for offer in cursor:
            offer["id"] = str(offer["_id"])
            del offer["_id"]
            
            # Get pet details
            if "pet_id" in offer:
                pet = await database.pets.find_one({"_id": ObjectId(offer["pet_id"])})
                if pet:
                    offer["pet_details"] = {
                        "id": str(pet["_id"]),
                        "name": pet.get("name", ""),
                        "type": pet.get("type", ""),
                        "photos": pet.get("photos", [])
                    }
                    
            # Get sender details
            sender = await database.users.find_one({"_id": ObjectId(offer["sender_id"])})
            if sender:
                offer["sender_details"] = {
                    "id": offer["sender_id"],
                    "name": sender.get("name", ""),
                    "avatar_url": sender.get("avatar_url")
                }
                
            offers.append(offer)
            
        return offers
        
    except Exception as e:
        print(f"Error getting conversation offers: {e}")
        return []


async def get_conversation_offer(
    conversation_id: str,
    offer_id: str,
    user_id: str,
    request: Request
) -> Optional[Dict[str, Any]]:
    """Get a specific offer in a conversation."""
    try:
        database = request.app.mongodb
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if not conversation:
            return None
            
        # Get offer
        offer = await database.conversation_offers.find_one({
            "_id": ObjectId(offer_id),
            "conversation_id": conversation_id
        })
        
        if not offer:
            return None
            
        offer["id"] = str(offer["_id"])
        del offer["_id"]
        
        # Get pet details
        if "pet_id" in offer:
            pet = await database.pets.find_one({"_id": ObjectId(offer["pet_id"])})
            if pet:
                offer["pet_details"] = {
                    "id": str(pet["_id"]),
                    "name": pet.get("name", ""),
                    "type": pet.get("type", ""),
                    "photos": pet.get("photos", [])
                }
                
        # Get sender details
        sender = await database.users.find_one({"_id": ObjectId(offer["sender_id"])})
        if sender:
            offer["sender_details"] = {
                "id": offer["sender_id"],
                "name": sender.get("name", ""),
                "avatar_url": sender.get("avatar_url")
            }
            
        return offer
        
    except Exception as e:
        print(f"Error getting conversation offer: {e}")
        return None


async def respond_to_offer(
    conversation_id: str,
    offer_id: str,
    accept: bool,
    user_id: str,
    message: Optional[str],
    request: Request
) -> Optional[Dict[str, Any]]:
    """Respond to an offer in a conversation."""
    try:
        database = request.app.mongodb
        from schemas.conversation import OfferStatus
        
        # Check if conversation exists and user is participant
        conversation = await database.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "participants": user_id
        })
        
        if not conversation:
            return None
            
        # Get offer
        offer = await database.conversation_offers.find_one({
            "_id": ObjectId(offer_id),
            "conversation_id": conversation_id
        })
        
        if not offer:
            return None
            
        # Make sure the user is not the sender and the offer is pending
        if offer["sender_id"] == user_id:
            return None
            
        if offer["status"] != OfferStatus.PENDING:
            return None
            
        # Update offer status
        now = datetime.utcnow()
        new_status = OfferStatus.ACCEPTED if accept else OfferStatus.REJECTED
        
        await database.conversation_offers.update_one(
            {"_id": ObjectId(offer_id)},
            {
                "$set": {
                    "status": new_status,
                    "responded_at": now
                }
            }
        )
        
        # Create a message in the conversation about the response
        status_text = "accepted" if accept else "rejected"
        content = f"Offer {status_text}"
        if message:
            content += f": {message}"
            
        message_doc = {
            "id": str(ObjectId()),
            "conversation_id": conversation_id,
            "sender_id": user_id,
            "content": content,
            "read": False,
            "is_offer_response": True,
            "offer_id": offer_id,
            "offer_accepted": accept,
            "created_at": now
        }
        
        # Add message to conversation
        await database.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message_doc},
                "$set": {"updated_at": now, "last_message": message_doc}
            }
        )
        
        # Get updated offer
        updated_offer = await get_conversation_offer(
            conversation_id=conversation_id,
            offer_id=offer_id,
            user_id=user_id,
            request=request
        )
        
        return updated_offer
        
    except Exception as e:
        print(f"Error responding to conversation offer: {e}")
        return None 