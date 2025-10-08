"""
Configuration settings for Here & Hear AI Service
"""

from pydantic import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # App Configuration
    APP_NAME: str = "Here & Hear AI Service"
    DEBUG: bool = False
    
    # API Keys
    OPENAI_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./here_hear.db"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Speech Processing
    SPEECH_RECOGNITION_ENGINE: str = "openai"
    WHISPER_MODEL: str = "base"
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_SIZE: int = 1024
    DEFAULT_LANGUAGE: str = "en-GB"
    DEFAULT_LOCALE: str = "en-GB"
    
    # Real-time Processing
    REALTIME_BUFFER_SIZE: int = 4096
    TRANSCRIPTION_CONFIDENCE_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 