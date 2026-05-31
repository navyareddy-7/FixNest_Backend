from pydantic import BaseModel
from typing import Optional

class RoomBase(BaseModel):
    room_number: str
    hostel_id: int
    capacity: Optional[int] = 4

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    status: Optional[str] = None
    occupied: Optional[int] = None

class RoomResponse(RoomBase):
    id: int
    occupied: int
    status: str
    hostel_name: Optional[str] = None

    class Config:
        from_attributes = True
