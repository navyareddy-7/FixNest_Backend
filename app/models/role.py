from sqlalchemy import Column, Integer, String
from app.db.session import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # 'super_admin', 'hostel_admin', 'worker', 'student'
