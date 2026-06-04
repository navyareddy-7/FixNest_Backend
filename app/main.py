# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth, complaints, admin, hostels, rooms, notices, emergency, emergency_hotline
from app.core.config import settings
from app.db.session import engine, Base, SessionLocal
from app.db.base import Base as DiscoveryBase
from app.models.user import User
from app.models.role import Role
from app.models.emergency import Emergency
from app.models.emergency_hotline import EmergencyHotline
from app.core import security

# Automatically create tables in local dev/production if they don't exist yet
try:
    DiscoveryBase.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully or already exist.")

    # Explicitly ensure new tables exist (belt-and-suspenders for Render cold starts)
    try:
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
        print(f"[INFO] Existing tables: {tables}")

        if "emergencies" not in tables:
            print("[WARN] emergencies table missing - creating now...")
            Emergency.__table__.create(bind=engine, checkfirst=True)
            print("[OK] emergencies table created.")
        else:
            print("[OK] emergencies table already exists.")

        if "emergency_hotlines" not in tables:
            print("[WARN] emergency_hotlines table missing - creating now...")
            EmergencyHotline.__table__.create(bind=engine, checkfirst=True)
            print("[OK] emergency_hotlines table created.")
        else:
            print("[OK] emergency_hotlines table already exists.")

    except Exception as ie:
        print(f"[WARN] Table inspection warning: {ie}")

    # Seed Roles
    db = SessionLocal()
    try:
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router,               prefix=f"{settings.API_V1_STR}/auth",               tags=["auth"])
app.include_router(complaints.router,         prefix=f"{settings.API_V1_STR}/complaints",         tags=["complaints"])
app.include_router(admin.router,              prefix=f"{settings.API_V1_STR}/admin",              tags=["admin"])
app.include_router(hostels.router,            prefix=f"{settings.API_V1_STR}/hostels",            tags=["hostels"])
app.include_router(rooms.router,              prefix=f"{settings.API_V1_STR}/rooms",              tags=["rooms"])
app.include_router(notices.router,            prefix=f"{settings.API_V1_STR}/notices",            tags=["notices"])
app.include_router(emergency.router,          prefix=f"{settings.API_V1_STR}/emergency",          tags=["emergency"])
app.include_router(emergency_hotline.router,  prefix=f"{settings.API_V1_STR}/emergency-hotline",  tags=["emergency-hotline"])


@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "FixNest Hostel Maintenance System API",
        "docs_url": "/docs"
    }
