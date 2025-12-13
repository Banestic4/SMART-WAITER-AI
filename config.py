import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Settings
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # DB Settings
    # DATABASE_URL = os.getenv("DATABASE_URL")
    
    # App Settings
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    APP_API_KEY = os.getenv("APP_API_KEY")
