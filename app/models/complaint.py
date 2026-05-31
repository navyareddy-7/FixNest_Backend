from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)  # plumbing, electrical, carpentry, housekeeping, other
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, in_progress, resolved
    severity = Column(String, default="medium", nullable=False)  # low, medium, high
    image_url = Column(String, nullable=True)
    resolved_image_url = Column(String, nullable=True)

    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("User", foreign_keys=[student_id], backref="complaints_filed")
    worker = relationship("User", foreign_keys=[worker_id], backref="tasks_assigned")
    hostel = relationship("Hostel", foreign_keys=[hostel_id])
    room = relationship("Room", foreign_keys=[room_id])

    @property
    def room_number(self):
        return self.room.room_number if self.room else ""

    @property
    def hostel_name(self):
        return self.hostel.name if self.hostel else ""
