import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Coachline Backend"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./coachline.db")
    
    # JWT Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-123456789")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # P3 Agents Integration
    P3_AGENT_BASE_URL: str = os.getenv("P3_AGENT_BASE_URL", "http://localhost:8001")
    AGENT_TIMEOUT_SECONDS: float = 5.0

    class Config:
        case_sensitive = True

settings = Settings()
