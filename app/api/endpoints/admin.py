from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.api import deps
from app.models.complaint import Complaint
from app.models.comment import Comment
from app.models.user import User
from app.models.role import Role
from app.models.hostel import Hostel
from app.schemas.complaint import ComplaintResponse, ComplaintAssign
from app.schemas.user import UserResponse, UserCreate
from app.core import security
from app.utils.notifications import send_expo_push_notification

router = APIRouter()

@router.get("/workers", response_model=List[UserResponse])
def get_workers(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Get all workers in the hostel system (Admins only).
    """
    from sqlalchemy.orm import joinedload
    query = db.query(User).options(joinedload(User.role_relation), joinedload(User.room), joinedload(User.hostel)).join(Role).filter(Role.name == "worker")
    if current_admin.role == "hostel_admin" and current_admin.hostel_id:
        query = query.filter(User.hostel_id == current_admin.hostel_id)
    return query.all()

@router.post("/workers", response_model=UserResponse)
def create_worker(
    *,
    db: Session = Depends(deps.get_db),
    worker_in: UserCreate,
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Create a new worker account (Admins only).
    """
    user = db.query(User).filter(User.email == worker_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists."
        )
        
    role_obj = db.query(Role).filter(Role.name == "worker").first()
    if not role_obj:
        raise HTTPException(status_code=500, detail="Default role configuration missing")

    db_worker = User(
        email=worker_in.email,
        hashed_password=security.get_password_hash(worker_in.password),
        full_name=worker_in.full_name,
        phone_number=worker_in.phone_number,
        staff_category=worker_in.staff_category or "General Maintenance Worker",
        role_id=role_obj.id,
        hostel_id=worker_in.hostel_id,
        status="active"
    )
    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)
    return db_worker

@router.post("/admins", response_model=UserResponse)
def create_hostel_admin(
    *,
    db: Session = Depends(deps.get_db),
    admin_in: UserCreate,
    current_super_admin: User = Depends(deps.get_current_active_super_admin)
) -> Any:
    """
    Create a new hostel admin account (Super Admins only).
    """
    user = db.query(User).filter(User.email == admin_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists."
        )
        
    role_obj = db.query(Role).filter(Role.name == "hostel_admin").first()
    if not role_obj:
        raise HTTPException(status_code=500, detail="Default role configuration missing")

    if admin_in.hostel_id:
        hostel = db.query(Hostel).filter(Hostel.id == admin_in.hostel_id).first()
        if not hostel:
            raise HTTPException(status_code=400, detail="Hostel does not exist")

    db_admin = User(
        email=admin_in.email,
        hashed_password=security.get_password_hash(admin_in.password),
        full_name=admin_in.full_name,
        phone_number=admin_in.phone_number,
        role_id=role_obj.id,
        hostel_id=admin_in.hostel_id,
        status="active"
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    # Also update the hostel to point back to this admin
    if db_admin.hostel_id:
        hostel = db.query(Hostel).filter(Hostel.id == db_admin.hostel_id).first()
        if hostel:
            hostel.admin_id = db_admin.id
            db.add(hostel)
            db.commit()

    return db_admin

@router.get("/admins", response_model=List[UserResponse])
def get_hostel_admins(
    db: Session = Depends(deps.get_db),
    current_super_admin: User = Depends(deps.get_current_active_super_admin)
) -> Any:
    """
    Get all hostel admins (Super Admins only).
    """
    admins = db.query(User).join(Role).filter(Role.name == "hostel_admin").all()
    return admins

from pydantic import BaseModel, EmailStr
from typing import Optional

class UserAdminUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    hostel_id: Optional[int] = None
    password: Optional[str] = None

@router.put("/admins/{id}", response_model=UserResponse)
def update_hostel_admin(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    admin_in: UserAdminUpdate,
    current_super_admin: User = Depends(deps.get_current_active_super_admin)
) -> Any:
    """
    Update a hostel admin (Super Admins only).
    """
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    role_obj = db.query(Role).filter(Role.name == "hostel_admin").first()
    if user.role_id != role_obj.id:
        raise HTTPException(status_code=400, detail="User is not a hostel admin")

    if admin_in.full_name is not None:
        user.full_name = admin_in.full_name
    if admin_in.phone_number is not None:
        user.phone_number = admin_in.phone_number
    if admin_in.hostel_id is not None:
        # Clear the old hostel's admin_id if necessary
        if user.hostel_id and user.hostel_id != admin_in.hostel_id:
            old_hostel = db.query(Hostel).filter(Hostel.id == user.hostel_id).first()
            if old_hostel and old_hostel.admin_id == user.id:
                old_hostel.admin_id = None
                db.add(old_hostel)

        user.hostel_id = admin_in.hostel_id
        
        # Update the new hostel to point to this admin
        new_hostel = db.query(Hostel).filter(Hostel.id == admin_in.hostel_id).first()
        if new_hostel:
            new_hostel.admin_id = user.id
            db.add(new_hostel)

    if admin_in.email is not None:
        user.email = admin_in.email
    
    if admin_in.password:
        user.hashed_password = security.get_password_hash(admin_in.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/admins/{id}")
def delete_hostel_admin(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_super_admin: User = Depends(deps.get_current_active_super_admin)
) -> Any:
    """
    Delete a hostel admin (Super Admins only).
    """
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    role_obj = db.query(Role).filter(Role.name == "hostel_admin").first()
    if user.role_id != role_obj.id:
        raise HTTPException(status_code=400, detail="User is not a hostel admin")
        
    # Safely remove this admin from any associated hostel block
    if user.hostel_id:
        hostel = db.query(Hostel).filter(Hostel.id == user.hostel_id).first()
        if hostel and hostel.admin_id == user.id:
            hostel.admin_id = None
            db.add(hostel)
            
    db.delete(user)
    db.commit()
    return {"status": "success", "message": "Admin deleted successfully"}

@router.get("/students", response_model=List[UserResponse])
def get_students(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Get all students in the hostel system (Admins only).
    """
    from sqlalchemy.orm import joinedload
    query = db.query(User).options(joinedload(User.role_relation), joinedload(User.room), joinedload(User.hostel)).join(Role).filter(Role.name == "student")
    if current_admin.role == "hostel_admin" and current_admin.hostel_id:
        query = query.filter(User.hostel_id == current_admin.hostel_id)
    return query.all()

@router.post("/students", response_model=UserResponse)
def create_student(
    *,
    db: Session = Depends(deps.get_db),
    student_in: UserCreate,
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Create a new student account (Admins only).
    """
    user = db.query(User).filter(User.email == student_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists."
        )
        
    role_obj = db.query(Role).filter(Role.name == "student").first()
    if not role_obj:
        raise HTTPException(status_code=500, detail="Default role configuration missing")

    from app.models.room import Room
    resolved_room_id = student_in.room_id
    if student_in.room_number and student_in.hostel_id:
        room = db.query(Room).filter(Room.room_number == student_in.room_number, Room.hostel_id == student_in.hostel_id).first()
        if not room:
            room = Room(room_number=student_in.room_number, hostel_id=student_in.hostel_id)
            db.add(room)
            db.commit()
            db.refresh(room)
        resolved_room_id = room.id

    db_student = User(
        email=student_in.email,
        hashed_password=security.get_password_hash(student_in.password),
        full_name=student_in.full_name,
        phone_number=student_in.phone_number,
        role_id=role_obj.id,
        hostel_id=student_in.hostel_id,
        room_id=resolved_room_id,
        status="active"
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@router.get("/users/search", response_model=List[UserResponse])
def search_users(
    query: str = Query(..., min_length=1, description="Search term to match against name, email, or phone"),
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Search users (students + workers) by name, email, or phone number.
    Results are scoped to the admin's hostel when applicable (Admins only).
    """
    from sqlalchemy.orm import joinedload

    search_pattern = f"%{query.strip()}%"

    base_query = (
        db.query(User)
        .options(joinedload(User.role_relation), joinedload(User.room))
        .join(Role)
        .filter(
            Role.name.in_(["student", "worker"]),
            or_(
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.phone_number.ilike(search_pattern),
            ),
        )
    )

    # Hostel admins can only see users within their hostel
    if current_admin.role == "hostel_admin" and current_admin.hostel_id:
        base_query = base_query.filter(User.hostel_id == current_admin.hostel_id)

    results = base_query.order_by(User.full_name).all()
    return results


# ─── Single-User CRUD ────────────────────────────────────────────────────────

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Fetch the full profile of a single student or worker by ID (Admins only).
    """
    from sqlalchemy.orm import joinedload

    print(f"[DEBUG] GET /admin/users/{user_id} — requested by admin id={current_admin.id} role={current_admin.role}")

    user = (
        db.query(User)
        .options(
            joinedload(User.role_relation),
            joinedload(User.room),
            joinedload(User.hostel),
        )
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        print(f"[DEBUG] User {user_id} not found in database")
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} was not found")

    print(f"[DEBUG] Found user: id={user.id} name={user.full_name} role={user.role} hostel_id={user.hostel_id}")

    # Hostel admins can only view users within their hostel
    if current_admin.role == "hostel_admin" and current_admin.hostel_id:
        if user.hostel_id != current_admin.hostel_id:
            print(f"[DEBUG] Access denied: admin hostel_id={current_admin.hostel_id} != user hostel_id={user.hostel_id}")
            raise HTTPException(status_code=403, detail="Access denied to this user")

    return user


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    staff_category: Optional[str] = None


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_profile(
    *,
    user_id: int,
    user_in: UserProfileUpdate,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Update a student or worker's profile fields (Admins only).
    """
    from sqlalchemy.orm import joinedload

    user = (
        db.query(User)
        .options(joinedload(User.role_relation), joinedload(User.room), joinedload(User.hostel))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hostel admins can only modify users in their hostel
    if current_admin.role == "hostel_admin" and current_admin.hostel_id:
        if user.hostel_id != current_admin.hostel_id:
            raise HTTPException(status_code=403, detail="Access denied to this user")

    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.phone_number is not None:
        user.phone_number = user_in.phone_number
    if user_in.staff_category is not None:
        user.staff_category = user_in.staff_category
    if user_in.email is not None:
        # Check for duplicate email
        existing = db.query(User).filter(User.email == user_in.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use by another account")
        user.email = user_in.email
    if user_in.password:
        user.hashed_password = security.get_password_hash(user_in.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Permanently delete a student or worker account (Admins only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hostel admins can only delete users in their hostel
    if current_admin.role == "hostel_admin" and current_admin.hostel_id:
        if user.hostel_id != current_admin.hostel_id:
            raise HTTPException(status_code=403, detail="Access denied to this user")

    # Prevent admins from deleting themselves
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"User '{user.full_name}' has been deleted"}


# ─── Status Toggle (kept separately for backward compatibility) ───────────────

@router.put("/users/{id}/status", response_model=UserResponse)
def update_user_status(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    status: str,
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Update status of a user (Admins only).
    """
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if status not in ["active", "suspended"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    user.status = status
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/complaints/{id}/assign", response_model=ComplaintResponse)
async def assign_complaint(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    assignment: ComplaintAssign,
    current_admin: User = Depends(deps.get_current_active_admin),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Assign a complaint to a maintenance worker (Admins only).
    """
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    worker = db.query(User).filter(User.id == assignment.worker_id).first()
    if not worker or worker.role != "worker" or worker.status != "active":
        raise HTTPException(status_code=400, detail="Specified user is not an active worker")

    old_worker_name = complaint.worker.full_name if complaint.worker else "Unassigned"
    complaint.worker_id = worker.id
    # Automatically move status from pending to in_progress upon assignment
    if complaint.status == "pending":
        complaint.status = "in_progress"
        
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Log system comment
    assign_comment = Comment(
        complaint_id=complaint.id,
        text=f"Complaint assigned to Worker {worker.full_name} by Admin {current_admin.full_name} (Previous: {old_worker_name}). Status is now 'In Progress'.",
        user_id=current_admin.id,
        is_system_action=True
    )
    db.add(assign_comment)
    db.commit()

    # Trigger push notifications in background
    # 1. Notify the worker
    if worker.push_token:
        background_tasks.add_task(
            send_expo_push_notification,
            worker.push_token,
            "New Task Assigned",
            f"You have been assigned to: Room ID {complaint.room_id} - {complaint.title}",
            {"complaint_id": complaint.id}
        )

    # 2. Notify the student
    student = db.query(User).filter(User.id == complaint.student_id).first()
    if student and student.push_token:
        background_tasks.add_task(
            send_expo_push_notification,
            student.push_token,
            "Worker Assigned to Complaint",
            f"Worker '{worker.full_name}' has been assigned to fix your issue: '{complaint.title}'",
            {"complaint_id": complaint.id}
        )

    return complaint

@router.get("/analytics")
def get_analytics(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Get complaint analytics and insights (Admins only).
    """
    is_hostel_admin = current_admin.role == "hostel_admin" and current_admin.hostel_id
    hostel_id = current_admin.hostel_id

    # Base complaint query
    base_complaint_query = db.query(Complaint)
    if is_hostel_admin:
        base_complaint_query = base_complaint_query.filter(Complaint.hostel_id == hostel_id)

    # 1. Total Status Breakdown
    status_counts = db.query(Complaint.status, func.count(Complaint.id))
    if is_hostel_admin:
        status_counts = status_counts.filter(Complaint.hostel_id == hostel_id)
    status_counts = status_counts.group_by(Complaint.status).all()
    
    status_map = {"pending": 0, "in_progress": 0, "resolved": 0}
    total = 0
    for status_name, count in status_counts:
        status_map[status_name] = count
        total += count
    status_map["total"] = total

    # 2. Category Breakdown
    category_counts = db.query(Complaint.category, func.count(Complaint.id))
    if is_hostel_admin:
        category_counts = category_counts.filter(Complaint.hostel_id == hostel_id)
    category_counts = category_counts.group_by(Complaint.category).all()
    
    category_map = {}
    for cat_name, count in category_counts:
        category_map[cat_name] = count

    # 3. Worker Workload (Active tasks assigned)
    active_worker_query = db.query(User.id, User.full_name, func.count(Complaint.id)).join(Complaint, Complaint.worker_id == User.id).filter(User.role_id == db.query(Role.id).filter(Role.name == "worker").scalar(), Complaint.status != "resolved")
    if is_hostel_admin:
         active_worker_query = active_worker_query.filter(User.hostel_id == hostel_id)
    active_worker_tasks = active_worker_query.group_by(User.id, User.full_name).all()
     
    workload = []
    for w_id, w_name, count in active_worker_tasks:
        workload.append({
            "worker_id": w_id,
            "worker_name": w_name,
            "active_tasks": count
        })

    # Ensure workers with 0 tasks are also included
    all_workers_query = db.query(User).filter(User.role_id == db.query(Role.id).filter(Role.name == "worker").scalar(), User.status == "active")
    if is_hostel_admin:
        all_workers_query = all_workers_query.filter(User.hostel_id == hostel_id)
    all_workers = all_workers_query.all()
    
    workload_worker_ids = [w["worker_id"] for w in workload]
    for worker in all_workers:
        if worker.id not in workload_worker_ids:
            workload.append({
                "worker_id": worker.id,
                "worker_name": worker.full_name,
                "active_tasks": 0
            })

    # Calculate average resolution time dynamically
    avg_res_query = db.query(func.avg(func.extract("epoch", Complaint.updated_at - Complaint.created_at)) / 3600).filter(Complaint.status == "resolved")
    if is_hostel_admin:
        avg_res_query = avg_res_query.filter(Complaint.hostel_id == hostel_id)
    avg_res_time = avg_res_query.scalar()
    
    average_hours = round(float(avg_res_time), 1) if avg_res_time is not None else 0.0

    # Calculate SLA Compliance (Resolved within 48 hours)
    total_res_query = db.query(func.count(Complaint.id)).filter(Complaint.status == "resolved")
    compliant_res_query = db.query(func.count(Complaint.id)).filter(Complaint.status == "resolved", func.extract("epoch", Complaint.updated_at - Complaint.created_at) / 3600 <= 48)
    
    if is_hostel_admin:
        total_res_query = total_res_query.filter(Complaint.hostel_id == hostel_id)
        compliant_res_query = compliant_res_query.filter(Complaint.hostel_id == hostel_id)
        
    total_resolved = total_res_query.scalar() or 0
    compliant_resolved = compliant_res_query.scalar() or 0

    sla_compliance = round((compliant_resolved / total_resolved) * 100, 1) if total_resolved > 0 else 100.0

    # Hostel Breakdown (Problems vs Solved)
    hostel_stats_query = db.query(Hostel.id, Hostel.name, Complaint.status, func.count(Complaint.id)).join(Complaint, Complaint.hostel_id == Hostel.id)
    if is_hostel_admin:
        hostel_stats_query = hostel_stats_query.filter(Hostel.id == hostel_id)
    hostel_stats = hostel_stats_query.group_by(Hostel.id, Hostel.name, Complaint.status).all()

    hostel_metrics = {}
    for h_id, h_name, status, count in hostel_stats:
        if h_id not in hostel_metrics:
            hostel_metrics[h_id] = {"name": h_name, "problems": 0, "solved": 0}
        
        if status in ["pending", "in_progress"]:
            hostel_metrics[h_id]["problems"] += count
        elif status == "resolved":
            hostel_metrics[h_id]["solved"] += count

    return {
        "status_metrics": status_map,
        "category_metrics": category_map,
        "worker_workload": workload,
        "average_resolution_hours": average_hours,
        "sla_compliance": sla_compliance,
        "hostel_metrics": list(hostel_metrics.values())
    }