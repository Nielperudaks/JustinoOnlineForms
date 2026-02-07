from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from utils.helpers import db, hash_password, verify_password, create_token, get_current_user
from fastapi import Depends
import uuid
from datetime import datetime, timezone

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


@auth_router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    user = await db.users.find_one({"email": req.email.lower()}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_token(user["id"], user["role"])
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return {"token": token, "user": safe_user}


@auth_router.get("/me")
async def get_me(user=Depends(get_current_user)):
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return safe_user
