"""Authentication endpoints — register, login, current user."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleRequest(BaseModel):
    credential: str  # Google ID token from the Sign-In button


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class UserResponse(BaseModel):
    id: int
    email: str


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email 格式不正確")
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="此 Email 已註冊")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email 或密碼錯誤")
    return TokenResponse(access_token=create_access_token(user.id), email=user.email)


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleRequest, db: AsyncSession = Depends(get_db)):
    """Verify a Google ID token, find-or-create the user, return our JWT."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google 登入尚未設定")

    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token

    def _verify():
        return id_token.verify_oauth2_token(
            body.credential, g_requests.Request(), settings.GOOGLE_CLIENT_ID
        )

    try:
        info = await asyncio.to_thread(_verify)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 驗證失敗")

    email = (info.get("email") or "").lower().strip()
    if not email or not info.get("email_verified", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無法取得已驗證的 Google Email")

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, password_hash="")  # Google account: no password
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), email=user.email)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email)
