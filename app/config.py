from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379"
    MODEL_PATH: str = "/app/weights/model.pt"
    SHARED_MEMORY_NAME: str = "ml_model_weights"
    MAX_QUEUE_SIZE: int = 1000
    WORKER_TIMEOUT_SEC: int = 30
    LOG_LEVEL: str = "info"
    MODEL_VERSION: str = "v1"
    
    class Config:
        env_file = ".env"

settings = Settings()
