from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.role import Role

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    staff_category = Column(String, nullable=True, default="General Maintenance Worker")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    status = Column(String, default="active", nullable=False)  # active, suspended
    push_token = Column(String, nullable=True)                 # Expo Push Notification token
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role_relation = relationship("Role", foreign_keys=[role_id])
    hostel = relationship("Hostel", foreign_keys=[hostel_id])
    room = relationship("Room", foreign_keys=[room_id])

    @property
    def role(self) -> str:
        return self.role_relation.name if self.role_relation else "student"

    @property
    def room_number(self) -> str:
        return self.room.room_number if self.room else ""

    @property
    def hostel_name(self) -> str:
        return self.hostel.name if self.hostel else ""
