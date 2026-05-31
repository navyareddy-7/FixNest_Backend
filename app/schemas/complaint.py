from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.user import UserResponse

class ComplaintBase(BaseModel):
    title: str
    description: str
    category: str  # plumbing, electrical, carpentry, housekeeping, other
    room_id: int
    hostel_id: int
    severity: Optional[str] = "medium" # low, medium, high

class ComplaintCreate(BaseModel):
    title: str
    description: str
    category: str
    room_id: int
    hostel_id: int
    severity: Optional[str] = "medium"
    image_url: Optional[str] = None

class ComplaintUpdate(BaseModel):
    status: Optional[str] = None # pending, in_progress, resolved
    severity: Optional[str] = None
    worker_id: Optional[int] = None

class ComplaintAssign(BaseModel):
    worker_id: int

class ComplaintStatusUpdate(BaseModel):
    status: str # pending, in_progress, resolved
    resolved_image_url: Optional[str] = None

class ComplaintResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    room_id: int
    hostel_id: int
    room_number: Optional[str] = None
    hostel_name: Optional[str] = None
    status: str
    severity: str
    image_url: Optional[str] = None
    resolved_image_url: Optional[str] = None
    student_id: int
    worker_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    student: Optional[UserResponse] = None
    worker: Optional[UserResponse] = None

    class Config:
        from_attributes = True
