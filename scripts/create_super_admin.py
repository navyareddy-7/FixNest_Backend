import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import engine
import app.db.base # Registers all models and relationships
from app.models.user import User
from app.models.role import Role
from app.core.security import get_password_hash

def seed_super_admin():
    db = Session(engine)
    try:
        # Find super_admin role
        role = db.query(Role).filter(Role.name == "super_admin").first()
        if not role:
            print("super_admin role not found. Please ensure roles are seeded.")
            return

        # Check if user already exists
        email = "admin@fixnest.com"
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Super Admin already exists with email: {email}")
            return

        # Create new super admin
        password = "SuperAdminPassword123!"
        hashed_pw = get_password_hash(password)

        super_admin = User(
            email=email,
            hashed_password=hashed_pw,
            full_name="Navya Reddy",
            phone_number="+91 1234567890",
            role_id=role.id,
            status="active"
        )
        
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        print(f"Success! Super Admin created.")
        print(f"Email: {email}")
        print(f"Password: {password}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_super_admin()
