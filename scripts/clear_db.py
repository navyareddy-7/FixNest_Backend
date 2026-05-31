import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine, Base
from app.models.user import User
from app.models.role import Role
from app.models.hostel import Hostel
from app.models.room import Room
from app.models.complaint import Complaint
from app.models.comment import Comment
from app.models.notice import Notice

from sqlalchemy import text

def clear_db():
    print("Dropping all tables...")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database cleared successfully!")

if __name__ == "__main__":
    clear_db()
