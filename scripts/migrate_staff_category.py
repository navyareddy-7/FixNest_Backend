import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import engine

def migrate():
    with engine.begin() as conn:
        print("Adding staff_category to users table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN staff_category VARCHAR;"))
            print("Successfully added staff_category column.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("Column staff_category already exists.")
            else:
                print(f"Error adding column: {e}")
                
        try:
            print("Updating existing workers to 'General Maintenance Worker'...")
            conn.execute(text("""
                UPDATE users 
                SET staff_category = 'General Maintenance Worker' 
                WHERE role_id = (SELECT id FROM roles WHERE name = 'worker')
                AND staff_category IS NULL;
            """))
            print("Successfully updated existing workers.")
        except Exception as e:
            print(f"Error updating workers: {e}")

if __name__ == "__main__":
    migrate()
