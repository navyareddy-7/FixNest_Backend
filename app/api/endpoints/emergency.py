"""
Emergency API endpoints — FIXED VERSION.

Critical fixes applied:
  1. BackgroundTasks must never have a default of None — FastAPI injects it automatically.
  2. Removed Optional[BackgroundTasks] anti-pattern from every PUT/POST handler.
  3. Added defensive try/except around the DB insert so errors are surfaced clearly.
  4. Route ordering: /sos, /active, /history declared BEFORE /{emergency_id} to prevent
     the dynamic path from swallowing named paths.
  5. Escalate: background_tasks properly injected (not defaulted to None).

Routes (all prefixed by /api/emergency via main.py):
  POST   /sos
  GET    /active
  GET    /history
  GET    /{emergency_id}
  PUT    /{emergency_id}/acknowledge
  PUT    /{emergency_id}/resolve
  PUT    /{emergency_id}/cancel
  POST   /{emergency_id}/escalate
"""
from typing import Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status as http_status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.api import deps
from app.models.emergency import Emergency
from app.models.user import User
from app.models.role import Role
from app.schemas.emergency import (
    EmergencyCreate,
    EmergencyResponse,
    EmergencyResolve,
    EmergencyCancel,
)
from app.utils.notifications import send_expo_push_notification

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _generate_ticket_number(db: Session) -> str:
    """Generate a sequential SOS ticket number like 'SOS-000042'."""
    count = db.query(Emergency).count()
    return f"SOS-{str(count + 1).zfill(6)}"


def _get_emergency_or_404(db: Session, emergency_id: int) -> Emergency:
    em = (
        db.query(Emergency)
        .options(
            joinedload(Emergency.student),
            joinedload(Emergency.assigned_technician),
            joinedload(Emergency.assigned_warden),
        )
        .filter(Emergency.id == emergency_id)
        .first()
    )
    if not em:
        raise HTTPException(status_code=404, detail="Emergency not found")
    return em


def _broadcast_emergency_sync(
    background_tasks: BackgroundTasks,
    db: Session,
    emergency: Emergency,
    title: str,
    body: str,
) -> None:
    """
    Queue push notifications (fire-and-forget via BackgroundTasks) to:
      - All active admins and workers who have a push token
    NOTE: Made synchronous (no await) so it can be used from both sync and async endpoints.
    """
    try:
        targets: List[User] = (
            db.query(User)
            .join(Role)
            .filter(
                Role.name.in_(["super_admin", "hostel_admin", "worker"]),
                User.status == "active",
                User.push_token.isnot(None),
            )
            .all()
        )
        data = {
            "type": "EMERGENCY_SOS",
            "emergency_id": emergency.id,
            "ticket_number": emergency.ticket_number,
            "emergency_type": emergency.emergency_type,
            "hostel": emergency.hostel_name,
            "room": emergency.room_number,
        }
        for t in targets:
            if t.push_token:
                background_tasks.add_task(
                    send_expo_push_notification,
                    t.push_token,
                    title,
                    body,
                    data,
                )
    except Exception as e:
        print(f"[Emergency] Failed to queue push notifications: {e}")


# ─── POST /sos ────────────────────────────────────────────────────────────────
# MUST be declared before /{emergency_id} to avoid route swallowing

@router.post("/sos", response_model=EmergencyResponse, status_code=http_status.HTTP_201_CREATED)
def create_sos(
    *,
    db: Session = Depends(deps.get_db),
    payload: EmergencyCreate,
    current_user: User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Student triggers emergency SOS.
    Creates an emergency record and notifies all admin/workers immediately.
    """
    print(f"[SOS] Received from user_id={current_user.id} type={payload.emergency_type}")

    # ── Build location snapshot from the logged-in student's profile ──────────
    hostel_name = ""
    room_number  = ""
    hostel_id    = None
    room_id      = None

    try:
        if current_user.hostel_id:
            from app.models.hostel import Hostel
            h = db.query(Hostel).filter(Hostel.id == current_user.hostel_id).first()
            if h:
                hostel_name = h.name
                hostel_id   = h.id
        if current_user.room_id:
            from app.models.room import Room
            r = db.query(Room).filter(Room.id == current_user.room_id).first()
            if r:
                room_number = r.room_number
                room_id     = r.id
    except Exception as e:
        print(f"[SOS] Warning: could not resolve hostel/room — {e}")

    print(f"[SOS] Location: hostel='{hostel_name}' room='{room_number}'")

    # ── Auto-assign the first active worker in the same hostel ────────────────
    # Map emergency type to preferred staff category
    category_map = {
        "stuck_lift": "Lift Technician",
        "fire": "Electrician",
        "electrical": "Electrician",
        "water_leakage": "Plumber",
        "security": "Security Staff",
        "locked_room": "Carpenter",
        "medical": "General Maintenance Worker",
        "other": "General Maintenance Worker"
    }
    preferred_category = category_map.get(payload.emergency_type, "General Maintenance Worker")

    technician = None
    try:
        if current_user.hostel_id:
            # First try to find a technician matching the preferred category
            technician = (
                db.query(User)
                .join(Role)
                .filter(
                    Role.name == "worker",
                    User.status == "active",
                    User.hostel_id == current_user.hostel_id,
                    User.staff_category == preferred_category,
                )
                .first()
            )
            # If no matching specialist is found, fallback to any active worker
            if not technician:
                technician = (
                    db.query(User)
                    .join(Role)
                    .filter(
                        Role.name == "worker",
                        User.status == "active",
                        User.hostel_id == current_user.hostel_id,
                    )
                    .first()
                )
    except Exception as e:
        print(f"[SOS] Warning: could not find technician — {e}")

    # ── Create the emergency record ───────────────────────────────────────────
    try:
        emergency = Emergency(
            ticket_number           = _generate_ticket_number(db),
            emergency_type          = payload.emergency_type,
            description             = payload.description,
            hostel_name             = hostel_name,
            room_number             = room_number,
            hostel_id               = hostel_id,
            room_id                 = room_id,
            status                  = "active",
            escalation_level        = 0,
            student_id              = current_user.id,
            assigned_technician_id  = technician.id if technician else None,
        )
        db.add(emergency)
        db.commit()
        db.refresh(emergency)
        print(f"[SOS] Created emergency id={emergency.id} ticket={emergency.ticket_number}")
    except Exception as e:
        db.rollback()
        print(f"[SOS] DB error: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create emergency ticket: {str(e)}"
        )

    # ── Reload with all relationships ─────────────────────────────────────────
    emergency = _get_emergency_or_404(db, emergency.id)

    # ── Queue push notifications (non-blocking) ───────────────────────────────
    type_label = payload.emergency_type.replace("_", " ").upper()
    _broadcast_emergency_sync(
        background_tasks,
        db,
        emergency,
        title=f"🚨 EMERGENCY SOS — {type_label}",
        body=(
            f"Student: {current_user.full_name} | "
            f"{hostel_name}, Room {room_number} | "
            f"Ticket: {emergency.ticket_number}"
        ),
    )

    if technician and technician.push_token:
        background_tasks.add_task(
            send_expo_push_notification,
            technician.push_token,
            f"🚨 EMERGENCY ASSIGNED — {type_label}",
            (
                f"You are assigned to: {current_user.full_name}, "
                f"{hostel_name} Rm {room_number}. Respond immediately!"
            ),
            {
                "type":          "EMERGENCY_ASSIGNED",
                "emergency_id":  emergency.id,
                "ticket_number": emergency.ticket_number,
            },
        )

    return emergency


# ─── GET /active ──────────────────────────────────────────────────────────────
# MUST be declared before /{emergency_id}

@router.get("/active", response_model=List[EmergencyResponse])
def get_active_emergencies(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Return all active/acknowledged emergencies visible to the caller."""
    query = (
        db.query(Emergency)
        .options(
            joinedload(Emergency.student),
            joinedload(Emergency.assigned_technician),
            joinedload(Emergency.assigned_warden),
        )
        .filter(Emergency.status.in_(["active", "acknowledged"]))
    )

    if current_user.role == "student":
        query = query.filter(Emergency.student_id == current_user.id)
    elif current_user.role == "worker":
        query = query.filter(
            or_(
                Emergency.assigned_technician_id == current_user.id,
                Emergency.hostel_id == current_user.hostel_id,
            )
        )
    elif current_user.role == "hostel_admin" and current_user.hostel_id:
        query = query.filter(Emergency.hostel_id == current_user.hostel_id)
    # super_admin sees all

    return query.order_by(Emergency.created_at.desc()).all()


# ─── GET /history ─────────────────────────────────────────────────────────────
# MUST be declared before /{emergency_id}

@router.get("/history", response_model=List[EmergencyResponse])
def get_emergency_history(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """All emergencies — role-scoped."""
    query = (
        db.query(Emergency)
        .options(
            joinedload(Emergency.student),
            joinedload(Emergency.assigned_technician),
            joinedload(Emergency.assigned_warden),
        )
    )
    if current_user.role == "student":
        query = query.filter(Emergency.student_id == current_user.id)
    elif current_user.role == "worker":
        query = query.filter(Emergency.assigned_technician_id == current_user.id)
    elif current_user.role == "hostel_admin" and current_user.hostel_id:
        query = query.filter(Emergency.hostel_id == current_user.hostel_id)

    return query.order_by(Emergency.created_at.desc()).limit(200).all()


# ─── GET /{emergency_id} ──────────────────────────────────────────────────────

@router.get("/{emergency_id}", response_model=EmergencyResponse)
def get_emergency(
    emergency_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    em = _get_emergency_or_404(db, emergency_id)
    if current_user.role == "student" and em.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised")
    return em


# ─── PUT /{emergency_id}/acknowledge ─────────────────────────────────────────
# NOTE: BackgroundTasks must NOT have a default=None — FastAPI auto-injects it

@router.put("/{emergency_id}/acknowledge", response_model=EmergencyResponse)
def acknowledge_emergency(
    emergency_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Any:
    """Technician or admin acknowledges the emergency."""
    em = _get_emergency_or_404(db, emergency_id)
    if em.status not in ("active",):
        return em  # idempotent

    em.status          = "acknowledged"
    em.acknowledged_at = datetime.now(timezone.utc)
    if current_user.role == "worker":
        em.assigned_technician_id = current_user.id
    db.commit()
    db.refresh(em)
    em = _get_emergency_or_404(db, emergency_id)

    student = db.query(User).filter(User.id == em.student_id).first()
    if student and student.push_token:
        background_tasks.add_task(
            send_expo_push_notification,
            student.push_token,
            "✅ Emergency Acknowledged",
            f"Your SOS ({em.ticket_number}) has been acknowledged. Help is on the way!",
            {"type": "EMERGENCY_ACKNOWLEDGED", "emergency_id": em.id},
        )
    return em


# ─── PUT /{emergency_id}/resolve ─────────────────────────────────────────────

@router.put("/{emergency_id}/resolve", response_model=EmergencyResponse)
def resolve_emergency(
    emergency_id: int,
    payload: EmergencyResolve,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Any:
    em = _get_emergency_or_404(db, emergency_id)
    if em.status == "resolved":
        return em

    em.status      = "resolved"
    em.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(em)
    em = _get_emergency_or_404(db, emergency_id)

    student = db.query(User).filter(User.id == em.student_id).first()
    if student and student.push_token:
        background_tasks.add_task(
            send_expo_push_notification,
            student.push_token,
            "✅ Emergency Resolved",
            f"Your emergency ({em.ticket_number}) has been resolved. Stay safe!",
            {"type": "EMERGENCY_RESOLVED", "emergency_id": em.id},
        )
    return em


# ─── PUT /{emergency_id}/cancel ───────────────────────────────────────────────

@router.put("/{emergency_id}/cancel", response_model=EmergencyResponse)
def cancel_emergency(
    emergency_id: int,
    payload: EmergencyCancel,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Student cancels their own false alarm."""
    em = _get_emergency_or_404(db, emergency_id)
    if current_user.role == "student" and em.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised")
    if em.status in ("resolved", "cancelled"):
        return em

    em.status = "cancelled"
    db.commit()
    db.refresh(em)
    return _get_emergency_or_404(db, emergency_id)


# ─── POST /{emergency_id}/escalate ────────────────────────────────────────────

@router.post("/{emergency_id}/escalate", response_model=EmergencyResponse)
def escalate_emergency(
    emergency_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Any:
    """Manually escalate an emergency to the next level."""
    em = _get_emergency_or_404(db, emergency_id)
    em.escalation_level = min(em.escalation_level + 1, 4)
    db.commit()
    db.refresh(em)
    em = _get_emergency_or_404(db, emergency_id)

    _broadcast_emergency_sync(
        background_tasks,
        db,
        em,
        title=f"🚨 ESCALATED (Level {em.escalation_level}) — {em.emergency_type.upper()}",
        body=(
            f"Emergency {em.ticket_number} escalated to Level {em.escalation_level}. "
            f"No response yet. Immediate action required!"
        ),
    )
    return em
