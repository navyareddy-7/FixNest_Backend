from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth, complaints, admin, hostels, rooms, notices
from app.core.config import settings
from app.db.session import engine, Base, SessionLocal
from app.db.base import Base as DiscoveryBase
from app.models.user import User
from app.models.role import Role
from app.core import security

# Automatically create tables in local dev/production if they don't exist yet
try:
    DiscoveryBase.metadata.create_all(bind=engine)
    print("Database tables created successfully or already exist.")
    
    # Automatic seed database
    db = SessionLocal()
    try:
        # Seed Roles Table First
        roles_to_seed = ["super_admin", "hostel_admin", "worker", "student"]
        role_map = {}
        for r_name in roles_to_seed:
            db_role = db.query(Role).filter(Role.name == r_name).first()
            if not db_role:
                db_role = Role(name=r_name)
                db.add(db_role)
                db.commit()
                db.refresh(db_role)
            role_map[r_name] = db_role.id
    except Exception as se:
        print(f"Error seeding roles: {se}")
    finally:
        db.close()
        
except Exception as e:
    print(f"Error initializing database tables: {e}")

app = FastAPI(
    title="FixNest Hostel Maintenance System API",
    description="Production-grade API for managing hostel student complaints, worker assignments, and admin insights.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS setup
# Allows mobile app local development, emulator hosts, and production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(complaints.router, prefix=f"{settings.API_V1_STR}/complaints", tags=["complaints"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(hostels.router, prefix=f"{settings.API_V1_STR}/hostels", tags=["hostels"])
app.include_router(rooms.router, prefix=f"{settings.API_V1_STR}/rooms", tags=["rooms"])
app.include_router(notices.router, prefix=f"{settings.API_V1_STR}/notices", tags=["notices"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "FixNest Hostel Maintenance System API",
        "docs_url": "/docs"
    }
