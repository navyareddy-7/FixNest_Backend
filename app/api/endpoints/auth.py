from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, Token

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

    if user_in.password is not None:
        current_user.hashed_password = security.get_password_hash(
            user_in.password
        )

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user
