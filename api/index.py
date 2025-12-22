import os
import sys

# Add the project root to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from telegram_bot import build_app
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global Application instance
ptb_application: Application = None

async def get_ptb_application() -> Application:
    """
    Lazy initialization of the PTB Application.
    This ensures it's created only once per warm container.
    """
    global ptb_application
    if ptb_application is None:
        logger.info("Building PTB Application...")
        ptb_application = build_app()
        await ptb_application.initialize()
    return ptb_application

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """
    Main Webhook Handler.
    Receives updates from Telegram and feeds them into the existing Bot Application.
    """
    try:
        ptb_app = await get_ptb_application()
        
        # Parse JSON
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        
        # Process Update
        await ptb_app.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/")
async def health_check():
    return {"status": "Smart Waiter Bot is Alive!"}
