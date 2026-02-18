"""Admin authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.models.user import User
from app.schemas.auth import AdminLogin, AdminRead, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def admin_login(body: AdminLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.Username == body.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.Hashed_Password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.Is_Active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )
    token = create_access_token(subject=user.User_ID, role="admin")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AdminRead)
async def get_me(current_user: User = Depends(get_current_admin)):
    return current_user
