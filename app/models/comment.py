from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # None for system updates without direct user actor
    text = Column(String, nullable=False)
    is_system_action = Column(Boolean, default=False, nullable=False) # True if auto-generated timeline event

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", backref="comments")
    user = relationship("User", backref="comments_made")
