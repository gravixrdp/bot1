import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.db import get_db
from ..core.redis_conn import redis
from ..models import Admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


async def create_session(username: str) -> Tuple[str, str]:
    sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(16)
    ttl = settings.SESSION_EXPIRE_MINUTES * 60
    await redis.hset(f"sess:{sid}", mapping={"username": username, "csrf": csrf, "created": str(datetime.utcnow())})
    await redis.expire(f"sess:{sid}", ttl)
    return sid, csrf


async def destroy_session(session_id: str):
    await redis.delete(f"sess:{session_id}")


async def get_current_admin(request: Request, db: AsyncSession = Depends(get_db)) -> Admin:
    sid = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not sid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await redis.hgetall(f"sess:{sid}")
    if not data:
        raise HTTPException(status_code=401, detail="Session expired")
    username = data.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    res = await db.execute(select(Admin).where(Admin.username == username))
    admin = res.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid session")
    return admin


def set_session_cookies(response: Response, sid: str, csrf: str):
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        sid,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf,
        httponly=False,  # readable by frontend to send as header
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
        path="/",
    )


async def require_csrf(request: Request):
    # Double submit cookie
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF validation failed")