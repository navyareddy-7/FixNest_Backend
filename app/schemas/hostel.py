from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HostelBase(BaseModel):
    name: str
    location: str
    admin_id: Optional[int] = None
    total_rooms: Optional[int] = 0

class HostelCreate(HostelBase):
    pass

class HostelResponse(HostelBase):
    id: int
    total_students: int
    admin_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
