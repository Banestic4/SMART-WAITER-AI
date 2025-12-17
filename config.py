import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Groq API Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEYS = os.getenv("GROQ_API_KEYS", "").split(",") if os.getenv("GROQ_API_KEYS") else []

    # Handle user putting list in singular variable
    if "," in GROQ_API_KEY:
        extra_keys = GROQ_API_KEY.split(",")
        GROQ_API_KEY = extra_keys[0] # Primary
        for k in extra_keys:
            if k not in GROQ_API_KEYS:
                GROQ_API_KEYS.append(k)

    if GROQ_API_KEY and GROQ_API_KEY not in GROQ_API_KEYS:
        GROQ_API_KEYS.insert(0, GROQ_API_KEY)
    
    # Clean keys
    GROQ_API_KEYS = [k.strip() for k in GROQ_API_KEYS if k.strip()]

    if not GROQ_API_KEYS:
        # Fallback or Error
        pass

    GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # Hugging Face Settings
    HF_TOKEN = os.getenv("HF_TOKEN")
    # Use NLLB-200 via Router (Try lowercase facebook org)
    HF_TRANSLATION_URL = "https://router.huggingface.co/hf-inference/models/facebook/nllb-200-distilled-600M"
    
    # DB Settings
    # DATABASE_URL = os.getenv("DATABASE_URL")
    
    # App Settings
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    APP_API_KEY = os.getenv("APP_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID") # Add this: ID of the Admin's Telegram Chat
