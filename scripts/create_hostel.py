import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.session import engine

def create_default_hostel():
    try:
        with engine.connect() as connection:
            print("Successfully connected to Supabase PostgreSQL!")
            
            # Check if hostel with id 1 exists
            result = connection.execute(text("SELECT id FROM hostels WHERE id = 1;"))
            hostel = result.fetchone()
            
            if not hostel:
                print("Hostel with id 1 not found. Creating default hostel...")
                connection.execute(text("INSERT INTO hostels (id, name, location) VALUES (1, 'Main Hostel', 'Default Location');"))
                connection.commit()
                print("Default hostel created successfully.")
            else:
                print("Hostel with id 1 already exists.")
                
    except Exception as e:
        print("Failed to connect to the database or execute query.")
        print(f"Error: {e}")

if __name__ == "__main__":
    create_default_hostel()
