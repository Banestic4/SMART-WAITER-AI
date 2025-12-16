import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config import Config
from agents.smart_waiter_agent import SmartWaiterAgent

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Initialize Agent
agent = SmartWaiterAgent()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    session_id = str(update.effective_chat.id)
    
    # Use synchronous run() in a thread to avoid blocking loop
    loop = asyncio.get_running_loop()
    full_response = await loop.run_in_executor(None, agent.run, "Hi", session_id)
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text=full_response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_text = update.message.text
    session_id = str(update.effective_chat.id)
    
    # Send "typing" action to show user we are working
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Use synchronous run() in a thread
    loop = asyncio.get_running_loop()
    full_response = await loop.run_in_executor(None, agent.run, user_text, session_id)
    
    if not full_response:
        full_response = "..."
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text=full_response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice notes."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice support is coming soon on Telegram! Please type your message for now.")

if __name__ == '__main__':
    if not Config.TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        exit(1)
        
    application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    voice_handler = MessageHandler(filters.VOICE, handle_voice)
    
    application.add_handler(start_handler)
    application.add_handler(msg_handler)
    application.add_handler(voice_handler)
    
    print("Telegram Bot is running...")
    application.run_polling()