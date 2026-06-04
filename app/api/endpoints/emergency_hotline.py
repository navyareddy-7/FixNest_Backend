"""
Emergency Hotline management endpoints.

Routes (prefixed by /api/emergency-hotline via main.py):
  GET    /              — get current active hotline (all authenticated users)
  POST   /              — create/replace hotline (admin only)
  PUT    /              — update hotline (admin only)
  GET    /contacts      — get emergency contacts for student SOS screen
                          Returns: warden (admin), technician (worker), hotline
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.emergency_hotline import EmergencyHotline
from app.models.user import User
from app.models.role import Role
from app.schemas.emergency_hotline import (
    EmergencyHotlineCreate,
    EmergencyHotlineUpdate,
    EmergencyHotlineResponse,
)

router = APIRouter()


# ─── Helper dependency ────────────────────────────────────────────────────────
def get_current_active_admin_or_super(
    current_user: User = Depends(deps.get_current_user),
) -> User:
    if current_user.role not in ["hostel_admin", "super_admin"]:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Admin access required to manage emergency hotlines.",
        )
    return current_user

# ─── GET / — fetch active hotline ────────────────────────────────────────────

@router.get("/", response_model=Optional[EmergencyHotlineResponse])
def get_hotline(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Return the current active hotline, or None if not configured."""
    hotline = (
        db.query(EmergencyHotline)
        .filter(EmergencyHotline.active == True)
        .order_by(EmergencyHotline.updated_at.desc())
        .first()
    )
    return hotline


# ─── POST / — create (admin only) ────────────────────────────────────────────

@router.post("/", response_model=EmergencyHotlineResponse, status_code=http_status.HTTP_201_CREATED)
def create_hotline(
    *,
    db: Session = Depends(deps.get_db),
    payload: EmergencyHotlineCreate,
    current_user: User = Depends(get_current_active_admin_or_super),
) -> Any:
    """
    Create a new hotline entry.
    Deactivates any previously active hotlines to ensure only one is active.
    """
    # Deactivate any existing active hotlines
    db.query(EmergencyHotline).filter(EmergencyHotline.active == True).update({"active": False})
    db.commit()

    hotline = EmergencyHotline(
        hotline_name   = payload.hotline_name,
        hotline_number = payload.hotline_number,
        active         = payload.active,
    )
    db.add(hotline)
    db.commit()
    db.refresh(hotline)
    return hotline


# ─── PUT / — update current hotline (admin only) ─────────────────────────────

@router.put("/", response_model=EmergencyHotlineResponse)
def update_hotline(
    *,
    db: Session = Depends(deps.get_db),
    payload: EmergencyHotlineUpdate,
    current_user: User = Depends(get_current_active_admin_or_super),
) -> Any:
    """Update the most recently created hotline."""
    hotline = (
        db.query(EmergencyHotline)
        .order_by(EmergencyHotline.id.desc())
        .first()
    )
    if not hotline:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No emergency hotline configured yet. Use POST to create one first.",
        )

    if payload.hotline_name is not None:
        hotline.hotline_name = payload.hotline_name
    if payload.hotline_number is not None:
        hotline.hotline_number = payload.hotline_number
    if payload.active is not None:
        # If activating this one, deactivate all others
        if payload.active:
            db.query(EmergencyHotline).filter(
                EmergencyHotline.id != hotline.id,
                EmergencyHotline.active == True,
            ).update({"active": False})
        hotline.active = payload.active

    db.commit()
    db.refresh(hotline)
    return hotline


# ─── GET /contacts — contacts for student SOS screen ─────────────────────────

@router.get("/contacts")
def get_emergency_contacts(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Return warden (admin profile), technician (assigned worker), and hotline.

    - Warden: first active hostel_admin (or super_admin) in the same hostel as the student.
              Falls back to any active admin if no hostel match.
    - Technician: the worker assigned to the current user's hostel (same logic as SOS auto-assign).
    - Hotline: the active EmergencyHotline record.
    """
    # ── Warden (admin) ────────────────────────────────────────────────────────
    warden_user: Optional[User] = None
    if current_user.hostel_id:
        warden_user = (
            db.query(User)
            .join(Role)
            .filter(
                Role.name.in_(["hostel_admin", "super_admin"]),
                User.status == "active",
                User.hostel_id == current_user.hostel_id,
            )
            .first()
        )
    if not warden_user:
        # fallback: any active admin
        warden_user = (
            db.query(User)
            .join(Role)
            .filter(
                Role.name.in_(["hostel_admin", "super_admin"]),
                User.status == "active",
            )
            .first()
        )

    # ── Technician (worker) ───────────────────────────────────────────────────
    technician_user: Optional[User] = None
    if current_user.hostel_id:
        technician_user = (
            db.query(User)
            .join(Role)
            .filter(
                Role.name == "worker",
                User.status == "active",
                User.hostel_id == current_user.hostel_id,
            )
            .first()
        )
    if not technician_user:
        technician_user = (
            db.query(User)
            .join(Role)
            .filter(
                Role.name == "worker",
                User.status == "active",
            )
            .first()
        )

    # ── Hotline ───────────────────────────────────────────────────────────────
    hotline = (
        db.query(EmergencyHotline)
        .filter(EmergencyHotline.active == True)
        .order_by(EmergencyHotline.updated_at.desc())
        .first()
    )

    return {
        "warden": {
            "name":  warden_user.full_name     if warden_user     else None,
            "phone": warden_user.phone_number  if warden_user     else None,
        },
        "technician": {
            "name":  technician_user.full_name    if technician_user else None,
            "phone": technician_user.phone_number if technician_user else None,
        },
        "hotline": {
            "name":  hotline.hotline_name   if hotline else "Emergency Hotline",
            "phone": hotline.hotline_number if hotline else None,
        },
    }


