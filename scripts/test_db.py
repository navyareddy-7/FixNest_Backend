import sys
import os
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine

def test_connection():
    try:
        # Try to connect and execute a simple query
        with engine.connect() as connection:
            print("Successfully connected to Supabase PostgreSQL!")
            
            # Fetch the roles to verify the tables are populated
            result = connection.execute(text("SELECT * FROM roles;"))
            roles = result.fetchall()
            
            print(f"Found {len(roles)} roles in the database:")
            for role in roles:
                print(f"- {role[1]}")
                
    except Exception as e:
        print("Failed to connect to the database.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection()
