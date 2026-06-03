"""
Emergency model — stored in the `emergencies` table.

Status lifecycle:
  active  →  acknowledged  →  resolved  |  cancelled (false alarm)

Escalation level tracks auto-escalation (0=none, 1, 2, 3, 4).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Emergency(Base):
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True)

    # Auto-generated ticket number e.g. "SOS-000001"
    ticket_number = Column(String, unique=True, index=True, nullable=False)

    # Emergency classification
    emergency_type = Column(String, nullable=False)   # stuck_lift, fire, medical, …
    description    = Column(String, nullable=True)    # optional free-text from student

    # Snapshot of location at time of SOS (avoids JOIN churn in urgent paths)
    hostel_name  = Column(String, nullable=False, default="")
    room_number  = Column(String, nullable=False, default="")
    hostel_id    = Column(Integer, ForeignKey("hostels.id"), nullable=True)
    room_id      = Column(Integer, ForeignKey("rooms.id"),   nullable=True)

    # Status: active | acknowledged | resolved | cancelled
    status           = Column(String, default="active",  nullable=False)
    escalation_level = Column(Integer, default=0,        nullable=False)

    # People involved
    student_id            = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_technician_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_warden_id     = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at     = Column(DateTime(timezone=True), nullable=True)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    student             = relationship("User", foreign_keys=[student_id])
    assigned_technician = relationship("User", foreign_keys=[assigned_technician_id])
    assigned_warden     = relationship("User", foreign_keys=[assigned_warden_id])
    hostel              = relationship("Hostel", foreign_keys=[hostel_id])
    room                = relationship("Room",   foreign_keys=[room_id])
