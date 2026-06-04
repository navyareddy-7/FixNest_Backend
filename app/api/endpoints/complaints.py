from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.api import deps
from app.models.complaint import Complaint
from app.models.comment import Comment
from app.models.user import User
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate, ComplaintAssign
from app.schemas.comment import CommentCreate, CommentResponse
from app.utils.notifications import send_expo_push_notification

router = APIRouter()

@router.post("/", response_model=ComplaintResponse)
async def create_complaint(
    *,
    db: Session = Depends(deps.get_db),
    complaint_in: ComplaintCreate,
    current_user: User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create a new complaint (Students only).
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can file complaints."
        )

    db_complaint = Complaint(
        title=complaint_in.title,
        description=complaint_in.description,
        category=complaint_in.category,
        room_id=complaint_in.room_id,
        hostel_id=complaint_in.hostel_id,
        severity=complaint_in.severity,
        image_url=complaint_in.image_url,
        student_id=current_user.id,
        status="pending"
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)

    # Automatically add a system comment log for creation
    creation_comment = Comment(
        complaint_id=db_complaint.id,
        text=f"Complaint successfully filed by Student {current_user.full_name}.",
        is_system_action=True
    )
    db.add(creation_comment)
    db.commit()

    # Trigger background notification to any active Admin users (simulated/real if tokens exist)
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        if admin.push_token:
            background_tasks.add_task(
                send_expo_push_notification,
                admin.push_token,
                "New Complaint Filed",
                f"Room ID {db_complaint.room_id} - {db_complaint.title}",
                {"complaint_id": db_complaint.id}
            )

    return db_complaint

@router.get("/", response_model=List[ComplaintResponse])
def read_complaints(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    status_filter: Optional[str] = None
) -> Any:
    """
    Retrieve complaints. Filters based on user role automatically.
    """
    from sqlalchemy.orm import joinedload
    query = db.query(Complaint).options(
        joinedload(Complaint.student),
        joinedload(Complaint.worker)
    )
    
    if current_user.role == "student":
        query = query.filter(Complaint.student_id == current_user.id)
    elif current_user.role == "worker":
        # Workers can only see complaints assigned to them
        query = query.filter(Complaint.worker_id == current_user.id)
    elif current_user.role == "hostel_admin" and current_user.hostel_id:
        # Hostel Admins only see complaints for their assigned hostel
        query = query.filter(Complaint.hostel_id == current_user.hostel_id)
    # Super Admins see everything
    
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
        
    complaints = query.order_by(Complaint.created_at.desc()).all()
    return complaints

@router.get("/search", response_model=List[ComplaintResponse])
def search_complaints(
    q: str = "",
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Search complaints by ticket number (partial or full ID match).
    Access is restricted by role — same rules as GET /complaints/.

    Query param:  ?q=<search_term>
      - Matches complaints whose string ID starts with or equals q (case-insensitive).
      - Returns all matching records ordered by created_at DESC.
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import cast, String

    query = db.query(Complaint).options(
        joinedload(Complaint.student),
        joinedload(Complaint.worker),
    )

    # Apply same role-based access control as the main list endpoint
    if current_user.role == "student":
        query = query.filter(Complaint.student_id == current_user.id)
    elif current_user.role == "worker":
        query = query.filter(Complaint.worker_id == current_user.id)
    elif current_user.role == "hostel_admin" and current_user.hostel_id:
        query = query.filter(Complaint.hostel_id == current_user.hostel_id)
    # super_admin / admin → no additional filter

    # Filter by ticket number (string prefix match on the integer id)
    term = q.strip()
    if term:
        try:
            # Optimised: if the term is a pure integer, match id exactly or as prefix
            int(term)
            query = query.filter(
                cast(Complaint.id, String).like(f"{term}%")
            )
        except ValueError:
            # Non-numeric input → return empty result set (ticket IDs are numeric)
            return []

    results = query.order_by(Complaint.created_at.desc()).all()
    return results

@router.get("/{id}", response_model=ComplaintResponse)
def read_complaint_by_id(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get complaint details by ID.
    """
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Check permissions
    if current_user.role == "student" and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this complaint")
        
    return complaint

@router.put("/{id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    status_update: ComplaintStatusUpdate,
    current_user: User = Depends(deps.get_current_active_worker_or_admin),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Update complaint status (Workers & Admins only).
    """
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    old_status = complaint.status
    new_status = status_update.status

    if old_status == new_status:
        return complaint

    complaint.status = new_status
    
    if new_status == "resolved" and status_update.resolved_image_url:
        complaint.resolved_image_url = status_update.resolved_image_url
        
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Log system comment
    status_comment = Comment(
        complaint_id=complaint.id,
        text=f"Status updated from '{old_status}' to '{new_status}' by {current_user.full_name}.",
        user_id=current_user.id,
        is_system_action=True
    )
    db.add(status_comment)
    db.commit()

    # Trigger push notification to student
    student = db.query(User).filter(User.id == complaint.student_id).first()
    if student and student.push_token:
        status_readable = new_status.replace("_", " ").title()
        background_tasks.add_task(
            send_expo_push_notification,
            student.push_token,
            f"FixNest Status Update",
            f"Your complaint '{complaint.title}' is now: {status_readable}",
            {"complaint_id": complaint.id}
        )

    return complaint

@router.post("/{id}/comments", response_model=CommentResponse)
def add_comment(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    comment_in: CommentCreate,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Add a comment/message to the complaint timeline.
    """
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Access control
    if current_user.role == "student" and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to post to this complaint")

    db_comment = Comment(
        complaint_id=id,
        user_id=current_user.id,
        text=comment_in.text,
        is_system_action=False
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/{id}/comments", response_model=List[CommentResponse])
def read_comments(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get all comments / activity logs for a complaint.
    """
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Access control
    if current_user.role == "student" and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view comments")

    comments = db.query(Comment).filter(Comment.complaint_id == id).order_by(Comment.created_at.asc()).all()
    return comments
