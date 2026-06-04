"""
EmergencyHotline model — stored in the `emergency_hotlines` table.
Only one record should be active at a time.
This is configured by Admin (Warden) and displayed to students on the SOS screen.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class EmergencyHotline(Base):
    __tablename__ = "emergency_hotlines"

    id              = Column(Integer, primary_key=True, index=True)
    hotline_name    = Column(String, nullable=False, default="Hostel Emergency Control Room")
    hotline_number  = Column(String, nullable=False)
    active          = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
