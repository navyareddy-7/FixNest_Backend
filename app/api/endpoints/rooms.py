from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.room import Room
from app.models.user import User
from app.schemas.room import RoomResponse, RoomCreate, RoomUpdate

router = APIRouter()

@router.get("/", response_model=List[RoomResponse])
def get_rooms(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get all active room allocations.
    """
    query = db.query(Room)
    if current_user.role != "super_admin" and current_user.hostel_id:
        query = query.filter(Room.hostel_id == current_user.hostel_id)
    return query.all()

@router.post("/", response_model=RoomResponse)
def create_room(
    *,
    db: Session = Depends(deps.get_db),
    room_in: RoomCreate,
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Register a new room block (Admins only).
    """
    db_room = Room(
        room_number=room_in.room_number,
        hostel_id=room_in.hostel_id,
        capacity=room_in.capacity,
        occupied=0,
        status="available"
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.put("/{id}", response_model=RoomResponse)
def update_room(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    room_update: RoomUpdate,
    current_admin: User = Depends(deps.get_current_active_admin)
) -> Any:
    """
    Update a room's occupancy or maintenance status (Admins only).
    """
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room_update.status is not None:
        room.status = room_update.status
        # If in maintenance, automatically evacuate occupancy
        if room_update.status == "maintenance":
            room.occupied = 0
            
    if room_update.occupied is not None:
        if room_update.occupied > room.capacity:
            raise HTTPException(status_code=400, detail="Occupancy exceeds capacity limit")
        room.occupied = room_update.occupied
        if room.occupied == room.capacity:
            room.status = "full"
        elif room.status != "maintenance":
            room.status = "available"
            
    db.add(room)
    db.commit()
    db.refresh(room)
    return room