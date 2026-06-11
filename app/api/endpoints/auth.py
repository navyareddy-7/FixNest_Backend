from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, Token, ChangePasswordRequest

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Login endpoint.
    Users can only login with credentials created by Admin.
    """

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not security.verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return {
        "access_token": security.create_access_token(
            user.id,
            expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current logged-in user profile.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    user_in: UserUpdate
) -> Any:
    """
    Update current user profile.
    """

    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name

    if user_in.phone_number is not None:
        current_user.phone_number = user_in.phone_number

    if user_in.push_token is not None:
        current_user.push_token = user_in.push_token

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/change-password")
def change_password(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    payload: ChangePasswordRequest
) -> Any:
    """
    Change user password securely by verifying the current password first.
    """
    logger.info("[CHANGE PASSWORD] Request received")
    
    if not current_user:
        logger.error("[CHANGE PASSWORD] User not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    logger.info("[CHANGE PASSWORD] User found")

    # 1. Verify current password
    if not security.verify_password(payload.current_password, current_user.hashed_password):
        logger.warning("[CHANGE PASSWORD] Current password incorrect")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    logger.info("[CHANGE PASSWORD] Password verified")
    
    # 2. Check that new password is different
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the old password"
        )
        
    # 3. Check confirm password matches
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # 4. Update password
    try:
        current_user.hashed_password = security.get_password_hash(payload.new_password)
        db.add(current_user)
        db.commit()
        logger.info("[CHANGE PASSWORD] Password updated")
        logger.info("[CHANGE PASSWORD] Success")
        
        return {
            "success": True,
            "message": "Password updated successfully"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"[CHANGE PASSWORD] Password update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password update failed"
        )
