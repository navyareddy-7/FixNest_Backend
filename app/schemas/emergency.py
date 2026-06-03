"""
Pydantic schemas for the Emergency API.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.user import UserResponse


# ─── Shared sub-schema ────────────────────────────────────────────────────────
class EmergencyUserInfo(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Create (POST /emergency/sos) ─────────────────────────────────────────────
class EmergencyCreate(BaseModel):
    emergency_type: str          # e.g. "stuck_lift"
    description:    Optional[str] = None


# ─── Update status ────────────────────────────────────────────────────────────
class EmergencyAcknowledge(BaseModel):
    pass   # no body needed — action is captured from auth token


class EmergencyResolve(BaseModel):
    resolution_note: Optional[str] = None


class EmergencyCancel(BaseModel):
    reason: Optional[str] = "False alarm"


# ─── Response ─────────────────────────────────────────────────────────────────
class EmergencyResponse(BaseModel):
    id:               int
    ticket_number:    str
    emergency_type:   str
    description:      Optional[str] = None
    hostel_name:      str
    room_number:      str
    hostel_id:        Optional[int] = None
    room_id:          Optional[int] = None
    status:           str
    escalation_level: int
    student_id:       int
    assigned_technician_id: Optional[int] = None
    assigned_warden_id:     Optional[int] = None
    student:              Optional[EmergencyUserInfo] = None
    assigned_technician:  Optional[EmergencyUserInfo] = None
    assigned_warden:      Optional[EmergencyUserInfo] = None
    created_at:      datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at:     Optional[datetime] = None
    updated_at:      datetime

    class Config:
        from_attributes = True
