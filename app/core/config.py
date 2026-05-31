import os
from dotenv import load_dotenv
load_dotenv()
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "39ee79989b5c2d30db5f5cc1d6c8b1115df8a5e12e09ff7b34b9d0de6d0e65d2")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 11520)) # Default: 8 days
    
    # Database Configuration (Supabase/PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fixnest")
    
    # Supabase Client Configuration
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
