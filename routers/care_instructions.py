from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import List, Dict, Any, Optional

from schemas.care_instructions import (
    CareInstructionsCreate, CareInstructionsUpdate, CareInstructionsOut
)
from dependencies.auth import get_current_active_user
from crud.care_instructions import (
    create_care_instructions, update_care_instructions, delete_care_instructions,
    get_care_instructions, check_care_instructions_access
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/pets/{pet_id}", response_model=CareInstructionsOut)
async def create_care_instructions_endpoint(
    pet_id: str,
    instructions: CareInstructionsCreate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Create care instructions for a pet"""
    owner_id = current_user["id"]
    
    result = await create_care_instructions(
        pet_id=pet_id,
        owner_id=owner_id,
        instructions_data=instructions.dict(),
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to create care instructions"
        )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.put("/pets/{pet_id}", response_model=CareInstructionsOut)
async def update_care_instructions_endpoint(
    pet_id: str,
    instructions: CareInstructionsUpdate,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Update care instructions for a pet"""
    owner_id = current_user["id"]
    
    result = await update_care_instructions(
        pet_id=pet_id,
        owner_id=owner_id,
        instructions_data=instructions.dict(exclude_unset=True),
        request=request
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Care instructions not found or you don't have permission to update them"
        )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.delete("/pets/{pet_id}")
async def delete_care_instructions_endpoint(
    pet_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Delete care instructions for a pet"""
    owner_id = current_user["id"]
    
    success = await delete_care_instructions(
        pet_id=pet_id,
        owner_id=owner_id,
        request=request
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Care instructions not found or you don't have permission to delete them"
        )
    
    return {"message": "Care instructions deleted successfully"}


@router.get("/pets/{pet_id}", response_model=CareInstructionsOut)
async def get_care_instructions_endpoint(
    pet_id: str,
    request: Request,
    current_user = Depends(get_current_active_user)
):
    """Get care instructions for a pet"""
    # Check if user has access to the care instructions
    has_access = await check_care_instructions_access(
        pet_id=pet_id,
        user_id=current_user["id"],
        request=request
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view these care instructions"
        )
    
    care_instructions = await get_care_instructions(
        pet_id=pet_id,
        request=request
    )
    
    if not care_instructions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Care instructions not found"
        )
    
    return care_instructions 