import sys
import os

# Add the current directory to sys.path so app can be imported properly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 so the mobile app can reach the backend over the local network
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
