from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime

from dependencies.auth import get_current_active_user
from utils.file_upload import upload_image_file
from schemas.user import (
    MeProfileOut, MeProfilePatch, PublicUserOut, UsernameAvailabilityResponse,
    ChangePasswordRequest,
    PrivacySettings, PrivacySettingsUpdate, BlockedUserOut,
    AddressOut, AddressCreate, AddressUpdate, SessionOut
)

router = APIRouter()


# Profile
@router.get("/users/me", response_model=MeProfileOut)
async def get_me(request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    doc = await db.users.find_one({"_id": ObjectId(current_user["id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(doc.get("_id")),
        "email": doc.get("email"),
        "username": doc.get("username"),
        "name": doc.get("name"),
        "bio": doc.get("bio"),
        "avatar_url": doc.get("avatar_url"),
        "birthdate": doc.get("birthdate"),
        "gender": doc.get("gender"),
        "location": doc.get("location"),
        "links": doc.get("links"),
    }


@router.patch("/users/me")
async def patch_me(payload: MeProfilePatch, request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    update = {k: v for k, v in payload.dict(exclude_unset=True).items()}
    update["updated_at"] = datetime.utcnow()

    # If username provided, ensure not taken (case-insensitive)
    if "username" in update and update["username"]:
        exists = await db.users.find_one({
            "username": {"$regex": f"^{update['username']}$", "$options": "i"},
            "_id": {"$ne": ObjectId(current_user["id"])}
        })
        if exists:
            raise HTTPException(status_code=422, detail=[{"loc": ["body", "username"], "msg": "Username already taken", "type": "value_error"}])

    res = await db.users.update_one({"_id": ObjectId(current_user["id"]) } , {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


@router.put("/users/me/avatar")
async def put_avatar(request: Request, file: UploadFile = File(...), current_user = Depends(get_current_active_user)):
    try:
        url = await upload_image_file(file, "avatars")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

    from bson import ObjectId
    db = request.app.mongodb
    await db.users.update_one({"_id": ObjectId(current_user["id"])}, {"$set": {"avatar_url": url, "updated_at": datetime.utcnow()}})
    return {"avatar_url": url}


@router.delete("/users/me/avatar")
async def delete_avatar(request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    await db.users.update_one({"_id": ObjectId(current_user["id"])}, {"$unset": {"avatar_url": ""}, "$set": {"updated_at": datetime.utcnow()}})
    return {"success": True}


@router.get("/users/{user_id}", response_model=PublicUserOut)
async def get_public_user(user_id: str, request: Request):
    from bson import ObjectId
    db = request.app.mongodb
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    # Respect privacy settings for public profile visibility (basic safeguard)
    privacy = await db.privacy_settings.find_one({"user_id": str(doc.get("_id"))})
    if privacy and privacy.get("profile_visibility") == "private":
        # Show minimal public info only
        public_loc = None
        loc = doc.get("location") or {}
        if loc:
            public_loc = {"city": loc.get("city"), "country": loc.get("country")}
        return {
            "id": str(doc.get("_id")),
            "username": doc.get("username"),
            "name": None,
            "bio": None,
            "avatar_url": doc.get("avatar_url"),
            "location": public_loc,
            "links": None,
        }
    public_loc = None
    loc = doc.get("location") or {}
    if loc:
        public_loc = {"city": loc.get("city"), "country": loc.get("country")}
    return {
        "id": str(doc.get("_id")),
        "username": doc.get("username"),
        "name": doc.get("name"),
        "bio": doc.get("bio"),
        "avatar_url": doc.get("avatar_url"),
        "location": public_loc,
        "links": doc.get("links"),
    }


# Username availability
@router.get("/users/availability", response_model=UsernameAvailabilityResponse)
async def username_availability(username: str = Query(..., min_length=3, max_length=30), request: Request = None):
    db = request.app.mongodb
    exists = await db.users.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
    available = exists is None
    suggestions: Optional[List[str]] = None
    if not available:
        base = ''.join([c for c in username.lower() if c.isalnum()])[:15]
        suffixes = ["_1", "_2", "_3", "_x", "_pro", "_dev"]
        suggestions = [f"{base}{s}" for s in suffixes]
    return {"available": available, "suggestions": suggestions}


# Security
@router.post("/auth/change-password")
async def change_password(payload: ChangePasswordRequest, request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    from core.security import verify_password, hash_password
    db = request.app.mongodb
    doc = await db.users.find_one({"_id": ObjectId(current_user["id"])})
    if not doc or not doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Password change not available")
    if not verify_password(payload.current_password, doc["password_hash"]):
        raise HTTPException(status_code=422, detail=[{"loc": ["body", "current_password"], "msg": "Incorrect password", "type": "value_error"}])
    await db.users.update_one({"_id": ObjectId(current_user["id"])}, {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": datetime.utcnow()}})
    return {"success": True}


@router.get("/auth/sessions", response_model=List[SessionOut])
async def list_sessions(request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    cursor = db.sessions.find({"user_id": current_user["id"]}).sort("created_at", -1)
    sessions: List[SessionOut] = []
    async for s in cursor:
        sessions.append(SessionOut(
            id=str(s.get("_id")),
            ip=s.get("ip"),
            user_agent=s.get("user_agent"),
            created_at=s.get("created_at"),
            last_seen_at=s.get("last_seen_at"),
            current=s.get("current", False)
        ))
    return sessions


@router.delete("/auth/sessions/{session_id}")
async def delete_session(session_id: str, request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    res = await db.sessions.delete_one({"_id": ObjectId(session_id), "user_id": current_user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@router.delete("/auth/sessions")
async def delete_all_sessions(request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    await db.sessions.delete_many({"user_id": current_user["id"]})
    return {"success": True}


# Notification settings are already covered by existing notifications router

# Privacy & messaging controls
@router.get("/users/me/privacy", response_model=PrivacySettings)
async def get_privacy(request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    doc = await db.privacy_settings.find_one({"user_id": current_user["id"]})
    if not doc:
        # defaults
        return PrivacySettings()
    doc.pop("_id", None)
    doc.pop("user_id", None)
    return PrivacySettings(**doc)


@router.patch("/users/me/privacy")
async def patch_privacy(payload: PrivacySettingsUpdate, request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    update = {k: v for k, v in payload.dict(exclude_unset=True).items()}
    update["updated_at"] = datetime.utcnow()
    await db.privacy_settings.update_one({"user_id": current_user["id"]}, {"$set": update, "$setOnInsert": {"user_id": current_user["id"]}}, upsert=True)
    return {"success": True}


@router.get("/users/me/blocks", response_model=List[BlockedUserOut])
async def get_blocks(request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    pipeline = [
        {"$match": {"user_id": current_user["id"]}},
        {"$lookup": {"from": "users", "localField": "blocked_user_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
    ]
    results: List[BlockedUserOut] = []
    async for b in db.blocks.aggregate(pipeline):
        results.append(BlockedUserOut(
            user_id=str(b.get("blocked_user_id")),
            name=b.get("user", {}).get("name") if b.get("user") else None,
            avatar_url=b.get("user", {}).get("avatar_url") if b.get("user") else None,
            blocked_at=b.get("blocked_at") or datetime.utcnow()
        ))
    return results


@router.post("/users/me/blocks")
async def add_block(body: Dict[str, str], request: Request, current_user = Depends(get_current_active_user)):
    blocked_user_id = body.get("user_id")
    if not blocked_user_id:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", "user_id"], "msg": "user_id required", "type": "value_error"}])
    from bson import ObjectId
    db = request.app.mongodb
    await db.blocks.update_one(
        {"user_id": current_user["id"], "blocked_user_id": ObjectId(blocked_user_id)},
        {"$set": {"blocked_at": datetime.utcnow()}},
        upsert=True
    )
    return {"success": True}


@router.delete("/users/me/blocks/{user_id}")
async def remove_block(user_id: str, request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    res = await db.blocks.delete_one({"user_id": current_user["id"], "blocked_user_id": ObjectId(user_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not blocked")
    return {"success": True}


# Addresses
@router.get("/users/me/addresses", response_model=List[AddressOut])
async def list_addresses(request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    cursor = db.addresses.find({"user_id": current_user["id"]}).sort("_id", -1)
    items: List[AddressOut] = []
    async for a in cursor:
        items.append(AddressOut(
            id=str(a.get("_id")),
            line1=a.get("line1"),
            line2=a.get("line2"),
            city=a.get("city"),
            state=a.get("state"),
            postal_code=a.get("postal_code"),
            country=a.get("country"),
            is_default=a.get("is_default", False)
        ))
    return items


@router.post("/users/me/addresses")
async def create_address(payload: AddressCreate, request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    doc = payload.dict()
    doc.update({"user_id": current_user["id"], "created_at": datetime.utcnow()})
    # ensure only one default
    if doc.get("is_default"):
        await db.addresses.update_many({"user_id": current_user["id"]}, {"$set": {"is_default": False}})
    res = await db.addresses.insert_one(doc)
    return {"id": str(res.inserted_id)}


@router.patch("/users/me/addresses/{addr_id}")
async def update_address(addr_id: str, payload: AddressUpdate, request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    update = {k: v for k, v in payload.dict(exclude_unset=True).items()}
    if update.get("is_default"):
        await db.addresses.update_many({"user_id": current_user["id"]}, {"$set": {"is_default": False}})
    res = await db.addresses.update_one({"_id": ObjectId(addr_id), "user_id": current_user["id"]}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Address not found")
    return {"success": True}


@router.delete("/users/me/addresses/{addr_id}")
async def delete_address(addr_id: str, request: Request, current_user = Depends(get_current_active_user)):
    from bson import ObjectId
    db = request.app.mongodb
    res = await db.addresses.delete_one({"_id": ObjectId(addr_id), "user_id": current_user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Address not found")
    return {"success": True}


# Account lifecycle
@router.post("/users/me/export")
async def export_me(request: Request, current_user = Depends(get_current_active_user)):
    db = request.app.mongodb
    await db.exports.insert_one({"user_id": current_user["id"], "requested_at": datetime.utcnow(), "status": "queued"})
    return {"success": True}


@router.delete("/users/me")
async def delete_me(body: Dict[str, Optional[str]], request: Request, current_user = Depends(get_current_active_user)):
    password = body.get("password") if body else None
    from bson import ObjectId
    db = request.app.mongodb
    # If user has a password (non-OAuth), require verification
    doc = await db.users.find_one({"_id": ObjectId(current_user["id"])})
    if doc and doc.get("password_hash"):
        from core.security import verify_password
        if not password or not verify_password(password, doc["password_hash"]):
            raise HTTPException(status_code=422, detail=[{"loc": ["body", "password"], "msg": "Password required to delete account", "type": "value_error"}])
    await db.users.delete_one({"_id": ObjectId(current_user["id"])})
    # cleanup related docs best-effort
    await db.sessions.delete_many({"user_id": current_user["id"]})
    await db.addresses.delete_many({"user_id": current_user["id"]})
    await db.blocks.delete_many({"user_id": current_user["id"]})
    return {"success": True}
