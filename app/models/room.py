from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String, index=True, nullable=False)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    capacity = Column(Integer, default=4, nullable=False)
    occupied = Column(Integer, default=0, nullable=False)
    status = Column(String, default="available", nullable=False)  # available, full, maintenance

    hostel = relationship("Hostel", foreign_keys=[hostel_id])

    @property
    def hostel_name(self) -> str:
        return self.hostel.name if self.hostel else "Unknown Hostel"
