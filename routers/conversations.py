from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Dict, Any, Optional

from schemas.conversation import (
    ConversationCreate, ConversationOut, ConversationWithMessages, 
    ConversationSummary, MessageCreate, MessageOut
)
from dependencies.auth import get_current_active_user
from crud.conversation import (
    create_conversation, get_conversation, send_message, get_user_conversations
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


@router.get("", response_model=List[ConversationSummary])
async def get_user_conversations_endpoint(
    request: Request,
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