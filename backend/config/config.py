import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

class Settings(BaseSettings):
    APP_NAME: str = "AIMedicalCoding"
    ENV: str = "development"
    DEBUG: bool = True
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    
    JWT_SECRET: str = "super-secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440
    
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-8b-8192"
    
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_ICD10_CM: str = "icd10_cm"
    QDRANT_COLLECTION_ICD10_PCS: str = "icd10_pcs"
    
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"
    
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SQLITE_DB_PATH: str = "sqlite:///./medical_coding.db"
    
    ICD10_CM_PATH: str = "../data/icd10-cm"
    ICD10_PCS_PATH: str = "../data/icd10-pcs"
    PROCESSED_DATA_PATH: str = "../data/processed"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
