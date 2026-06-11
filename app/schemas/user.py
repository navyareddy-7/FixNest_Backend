from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    staff_category: Optional[str] = None
    role: Optional[str] = "student" # student, worker, admin
    hostel_id: Optional[int] = None
    room_id: Optional[int] = None
    push_token: Optional[str] = None
    device_type: Optional[str] = None
    push_token_updated_at: Optional[datetime] = None

class UserCreate(UserBase):
    password: str
    room_number: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    push_token: Optional[str] = None
    device_type: Optional[str] = None
    push_token_updated_at: Optional[datetime] = None

class UserInDBBase(UserBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserResponse(UserInDBBase):
    room_number: Optional[str] = None
    hostel_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenPayload(BaseModel):
    sub: Optional[int] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class TokenData(BaseModel):
    username: Optional[str] = None

