from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.notice import Notice
from app.models.user import User
from app.schemas.notice import NoticeResponse, NoticeCreate

router = APIRouter()

@router.get("/", response_model=List[NoticeResponse])
def get_notices(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get all active notices. Students see notices specific to their hostel or global alerts.
    """
    return db.query(Notice).order_by(Notice.created_at.desc()).all()

@router.post("/", response_model=NoticeResponse)
def create_notice(
    *,
    db: Session = Depends(deps.get_db),
    notice_in: NoticeCreate,
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Create a new notice alert (Admins only).
    """
    db_notice = Notice(
        title=notice_in.title,
        content=notice_in.content,
        hostel_name=notice_in.hostel_name,
        created_by_id=current_admin.id
    )
    db.add(db_notice)
    db.commit()
    db.refresh(db_notice)
    return db_notice

@router.delete("/{id}")
def delete_notice(
    id: int,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Delete a notice (Admins only).
    """
    notice = db.query(Notice).filter(Notice.id == id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    db.delete(notice)
    db.commit()
    return {"status": "success", "detail": "Notice deleted successfully"}