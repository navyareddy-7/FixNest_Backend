from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class EmergencyHotlineCreate(BaseModel):
    hotline_name: str = "Hostel Emergency Control Room"
    hotline_number: str
    active: bool = True


class EmergencyHotlineUpdate(BaseModel):
    hotline_name: Optional[str] = None
    hotline_number: Optional[str] = None
    active: Optional[bool] = None


class EmergencyHotlineResponse(BaseModel):
    id: int
    hotline_name: str
    hotline_number: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
