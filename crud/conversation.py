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
            message = {
                "id": str(ObjectId()),
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
        message = {
            "id": str(ObjectId()),
            "sender_id": sender_id,
            "content": data.message,
            "read": False,
            "attachment_urls": data.attachment_urls,
            "created_at": now
        }
        
        conversation_doc = {
            "participants": [sender_id, data.recipient_id],
            "messages": [message],
            "last_message": message,
            "created_at": now,
            "updated_at": now
        }
        
        if data.related_pet_id:
            conversation_doc["related_pet_id"] = data.related_pet_id
            
        if data.related_booking_id:
            conversation_doc["related_booking_id"] = data.related_booking_id
        
        # Insert conversation
        result = await database.conversations.insert_one(conversation_doc)
        
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
    limit: int = 20
) -> Tuple[List[Dict[str, Any]], int]:
    """Get user's conversations with pagination."""
    try:
        database = request.app.mongodb
        skip = (page - 1) * limit
        
        # Count total conversations
        total = await database.conversations.count_documents({"participants": user_id})
        
        # Get conversations with pagination
        conversations = []
        async for conversation in database.conversations.find(
            {"participants": user_id}
        ).sort("updated_at", -1).skip(skip).limit(limit):
            conversation["id"] = str(conversation["_id"])
            del conversation["_id"]
            
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