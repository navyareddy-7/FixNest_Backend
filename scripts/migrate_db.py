import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import engine

def migrate():
    with engine.begin() as conn:
        print("Adding resolved_image_url to complaints table...")
        # Catch errors if column already exists (sqlite doesn't support IF NOT EXISTS for columns, but we are using Postgres according to .env)
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN resolved_image_url VARCHAR;"))
            print("Successfully added resolved_image_url.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("Column resolved_image_url already exists.")
            else:
                print(f"Error: {e}")
                
if __name__ == "__main__":
    migrate()
