from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, File, UploadFile
from typing import List, Dict, Any, Optional

from schemas.conversation import (
    ConversationCreate, ConversationOut, ConversationWithMessages, 
    ConversationSummary, MessageCreate, MessageOut, ArchiveConversationRequest,
    ConversationOfferCreate, ConversationOfferOut, OfferResponse
)
from dependencies.auth import get_current_active_user
from crud.conversation import (
    create_conversation, get_conversation, send_message, get_user_conversations,
    mark_conversation_as_read, delete_message, send_image_message, archive_conversation,
    create_conversation_offer, get_conversation_offers, get_conversation_offer, respond_to_offer
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ConversationOut)
async def create_conversation_endpoint(
    data: ConversationCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create a new conversation with another user"""
    # Validate recipient is not the current user
    if data.recipient_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a conversation with yourself"
        )
        
    conversation = await create_conversation(
        data=data,
        sender_id=current_user["id"],
        request=request
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )
        
    return conversation


@router.put("/{conversation_id}/read", status_code=status.HTTP_200_OK)
async def mark_all_as_read_endpoint(
    conversation_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Mark all messages in a conversation as read"""
    success = await mark_conversation_as_read(
        conversation_id=conversation_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you don't have access"
        )
    
    return {"status": "success", "message": "All messages marked as read"}


@router.delete("/{conversation_id}/messages/{message_id}", status_code=status.HTTP_200_OK)
async def delete_message_endpoint(
    conversation_id: str,
    message_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete a message (only sender can delete their own messages)"""
    success = await delete_message(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found, or you don't have permission to delete it"
        )
    
    return {"status": "success", "message": "Message deleted"}


@router.post("/{conversation_id}/images", response_model=MessageOut)
async def send_images_endpoint(
    conversation_id: str,
    request: Request,
    files: List[UploadFile] = File(..., description="Image files to send"),
    current_user = Depends(get_current_active_user)
):
    """Send image messages in a conversation"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No images provided"
        )
    
    # Check file types
    for file in files:
        content_type = file.content_type
        if not content_type or not content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not an image"
            )
    
    result = await send_image_message(
        conversation_id=conversation_id,
        user_id=current_user["id"],
        files=files,
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or failed to upload images"
        )
    
    return result


@router.put("/{conversation_id}/archive", status_code=status.HTTP_200_OK)
async def archive_conversation_endpoint(
    conversation_id: str,
    archive_request: ArchiveConversationRequest,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Archive or unarchive a conversation"""
    success = await archive_conversation(
        conversation_id=conversation_id,
        user_id=current_user["id"],
        archive=archive_request.archive,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you don't have access"
        )
    
    action = "archived" if archive_request.archive else "unarchived"
    return {"status": "success", "message": f"Conversation {action}"}


@router.get("", response_model=List[ConversationSummary])
async def get_user_conversations_endpoint(
    request: Request,
    archived: bool = Query(False, description="If true, return archived conversations instead of active ones"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get list of user's conversations"""
    conversations, _ = await get_user_conversations(
        user_id=current_user["id"],
        request=request,
        page=page,
        limit=per_page
    )
    
    # Filter by archived status
    if archived:
        conversations = [c for c in conversations if current_user["id"] in c.get("archived_by", [])]
    else:
        conversations = [c for c in conversations if current_user["id"] not in c.get("archived_by", [])]
    
    return conversations


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation_endpoint(
    conversation_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get a specific conversation with messages"""
    conversation = await get_conversation(
        conversation_id=conversation_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you don't have access"
        )
        
    return conversation


@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def send_message_endpoint(
    conversation_id: str,
    message: MessageCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Send a new message in a conversation"""
    result = await send_message(
        conversation_id=conversation_id,
        message_data=message,
        sender_id=current_user["id"],
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you don't have access"
        )
        
    return result 


@router.post("/{conversation_id}/offers", response_model=ConversationOfferOut)
async def create_offer_endpoint(
    conversation_id: str,
    offer_data: ConversationOfferCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create a new offer in a conversation"""
    offer = await create_conversation_offer(
        conversation_id=conversation_id,
        offer_data=offer_data.dict(),
        sender_id=current_user["id"],
        request=request
    )
    
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found, you don't have access, or the pet doesn't exist"
        )
    
    return offer


@router.get("/{conversation_id}/offers", response_model=List[ConversationOfferOut])
async def get_offers_endpoint(
    conversation_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get all offers in a conversation"""
    offers = await get_conversation_offers(
        conversation_id=conversation_id,
        user_id=current_user["id"],
        request=request
    )
    
    return offers


@router.get("/{conversation_id}/offers/{offer_id}", response_model=ConversationOfferOut)
async def get_offer_endpoint(
    conversation_id: str,
    offer_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get a specific offer in a conversation"""
    offer = await get_conversation_offer(
        conversation_id=conversation_id,
        offer_id=offer_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found or you don't have access"
        )
    
    return offer


@router.post("/{conversation_id}/offers/{offer_id}/respond", response_model=ConversationOfferOut)
async def respond_to_offer_endpoint(
    conversation_id: str,
    offer_id: str,
    response: OfferResponse,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Respond to an offer (accept or reject)"""
    updated_offer = await respond_to_offer(
        conversation_id=conversation_id,
        offer_id=offer_id,
        accept=response.accept,
        user_id=current_user["id"],
        message=response.message,
        request=request
    )
    
    if not updated_offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found, you don't have access, or the offer is no longer pending"
        )
    
    return updated_offer 