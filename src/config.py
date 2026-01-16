from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/attempts_db"
    nats_url: str = "nats://localhost:4222"
    service_name: str = "attempt-service"
    port: int = 8003
    logfire_token: str | None = None
    logfire_service_name: str | None = None
    
    class Config:
        env_file = ".env"

settings = Settings()