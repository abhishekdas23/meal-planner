from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import get_db
from app.models import Household, User
from app.schemas import LoginRequest, LoginResponse

router = APIRouter()
security = HTTPBearer(auto_error=False)


def create_token(user_id: int, user_name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.token_expire_days)
    payload = {"sub": str(user_id), "name": user_name, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Verify PIN
    result = await db.execute(select(Household))
    household = result.scalar_one_or_none()
    if not household:
        raise HTTPException(status_code=500, detail="Household not configured")

    if not bcrypt.checkpw(req.pin.encode(), household.pin_hash.encode()):
        raise HTTPException(status_code=401, detail="Wrong PIN")

    # Find user
    result = await db.execute(select(User).where(User.name == req.user_name))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_token(user.id, user.name)
    return LoginResponse(token=token, user_id=user.id, user_name=user.name)


@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "name": u.name} for u in users]
