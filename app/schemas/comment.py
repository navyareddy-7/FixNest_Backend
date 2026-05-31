from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.user import UserResponse

class CommentCreate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    id: int
    complaint_id: int
    user_id: Optional[int] = None
    text: str
    is_system_action: bool
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True
