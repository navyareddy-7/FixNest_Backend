from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.hostel import Hostel
from app.models.user import User
from app.schemas.hostel import HostelResponse, HostelCreate

router = APIRouter()

@router.get("/", response_model=List[HostelResponse])
def get_hostels(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get all active hostel blocks.
    """
    return db.query(Hostel).all()

@router.post("/", response_model=HostelResponse)
def create_hostel(
    *,
    db: Session = Depends(deps.get_db),
    hostel_in: HostelCreate,
    current_super_admin: User = Depends(deps.get_current_active_super_admin)
) -> Any:
    """
    Register a new hostel block (Super Admins only).
    """
    db_hostel = db.query(Hostel).filter(Hostel.name == hostel_in.name).first()
    if db_hostel:
        raise HTTPException(
            status_code=400,
            detail="Hostel block with this name already exists."
        )
        
    db_hostel = Hostel(
        name=hostel_in.name,
        location=hostel_in.location,
        admin_id=hostel_in.admin_id,
        total_rooms=hostel_in.total_rooms,
        total_students=0
    )
    db.add(db_hostel)
    db.commit()
    db.refresh(db_hostel)
    return db_hostel
