from fastapi import FastAPI
import asyncio
import os
import uvicorn
from telegram_bot import build_app
from config import Config

app = FastAPI()

# Global variable to hold the bot application
bot_app = None

@app.on_event("startup")
async def startup_event():
    """Start the Telegram Bot in Polling Mode when FastAPI starts."""
    global bot_app
    print("Starting Telegram Bot via FastAPI...")
    
    if not Config.TELEGRAM_TOKEN:
        print("WARNING: No TELEGRAM_TOKEN found. Bot will not start.")
        return

    # Build the application using our factory
    bot_app = build_app()
    
    # Initialize the bot explicitly (ensures ExtBot is ready)
    if bot_app:
        await bot_app.initialize()
        await bot_app.start()
        
        # Start Polling in a non-blocking way
        # Note: In PTB v20+, start_polling() is asynchronous and doesn't block if run in task?
        # Actually updater.start_polling() is a high level wrapper.
        # We need to manually control the updater or just create a task for run_polling?
        # run_polling() normally handles signals which conflicts with Uvicorn.
        # So we use updater.start_polling() directly.
        
        if bot_app.updater:
            await bot_app.updater.start_polling()
            print("Bot Polling Started.")
        else:
            print("Error: No updater found on bot app.")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the bot gracefully."""
    print("Shutting down bot...")
    if bot_app and bot_app.updater:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

@app.get("/")
def health_check():
    """Render Health Check endpoint."""
    return {"status": "ok", "service": "Smart Waiter Bot"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
