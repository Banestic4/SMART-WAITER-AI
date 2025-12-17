import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from agents.smart_waiter_agent import SmartWaiterAgent

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Handle specific network errors
    from telegram.error import Conflict, NetworkError
    
    if isinstance(context.error, Conflict):
        logger.critical("Conflict: Another instance of the bot is running. Shutting down...")
        import os
        os._exit(1) # Hard exit to stop the loop
        
    # Optional: Send error to admin
    # if Config.TELEGRAM_ADMIN_CHAT_ID:
    #     await context.bot.send_message(chat_id=Config.TELEGRAM_ADMIN_CHAT_ID, text=f"⚠️ Bot Error: {context.error}")


# Initialize Agent
agent = SmartWaiterAgent()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    # Show Session Choice Options
    keyboard = [
        [
            InlineKeyboardButton("🆕 Start Fresh (Reset Memory)", callback_data="session_new"),
            InlineKeyboardButton("💬 Continue Chat", callback_data="session_continue")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="👋 Welcome to Smart Waiter!\nWould you like to start a new order or continue where you left off?",
        reply_markup=reply_markup
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactions with Inline Buttons (Admin Interface)."""
    query = update.callback_query
    await query.answer() # Acknowledge interaction IMMEDIATELY
    
    print(f"DEBUG: Callback received: {query.data}")
    
    data = query.data
    # Format: action_orderId (e.g., confirm_12345)
    
    if not data:
        print("DEBUG: No data in callback")
        return

    parts = data.split("_")
    action = parts[0]
    
    if len(parts) < 2:
        return
        
    order_id = parts[1]
    
    # --- ADMIN ACTIONS ---
    if action in ["approve", "deny"]:
        # Verify Admin (Double check security)
        if str(update.effective_chat.id) != str(Config.TELEGRAM_ADMIN_CHAT_ID):
            await query.edit_message_text(text="⛔ Unauthorized interaction.")
            return

        from storage import db
        
        if action == "approve":
            # QUICK FIX: Remove buttons immediately to prevent double-click
            await query.edit_message_text(text=f"⏳ Verifying Order {order_id}...")
    
        # 1. Update Database
        db.execute_update("UPDATE orders SET status = 'PAID' WHERE order_id = ?", (order_id,))
        
        # 2. Notify Client
        rows = db.execute_query("SELECT table_id FROM orders WHERE order_id = ?", (order_id,))
        if rows:
            stored_session_id = rows[0]['table_id']
            # Extract real chat ID (legacy "12345" or new "12345_1")
            real_chat_id = stored_session_id.split('_')[0]
            
            # Inject System Event using the STORED session ID to match agent state
            loop = asyncio.get_running_loop()
            
            result = await loop.run_in_executor(None, agent.run, "SYSTEM_EVENT: ADMIN_VERIFIED", stored_session_id)
            full_response, metadata = result
            
            await context.bot.send_message(chat_id=real_chat_id, text=full_response)
            
            if metadata.get("reset_session"):
                db.increment_session_version(real_chat_id)
        
        # 3. Update Admin UI (Final confirmation)
        await query.edit_message_text(text=f"✅ Order {order_id} Verified by You.")
        
    elif action == "deny":
        # Remove buttons immediately
        await query.edit_message_text(text=f"⏳ Denying Order {order_id}...")
        
        # Notify Client of failure via AGENT (so state clears)
        rows = db.execute_query("SELECT table_id FROM orders WHERE order_id = ?", (order_id,))
        if rows:
            stored_session_id = rows[0]['table_id']
            # Inject System Event
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, agent.run, "SYSTEM_EVENT: ADMIN_DENIED", stored_session_id)
            full_response, metadata = result
            
            # Send the agent's response (which should be "Payment verification failed...")
            real_chat_id = stored_session_id.split('_')[0]
            await context.bot.send_message(chat_id=real_chat_id, text=full_response)
            
            if metadata.get("reset_session"):
                db.increment_session_version(real_chat_id)

        await query.edit_message_text(text=f"❌ Order {order_id} Denied.")

    # --- CLIENT SESSION ACTIONS ---
    elif action == "session":
        mode = parts[1] # new or continue
        user_id = str(update.effective_chat.id)
        from storage import db
        
        # Destroy buttons
        await query.delete_message()
        
        if mode == "new":
            db.increment_session_version(user_id)
            await context.bot.send_message(chat_id=user_id, text="🧹 **Memory Wiped.** Starting a new session...")
        else:
             await context.bot.send_message(chat_id=user_id, text="💬 **Resuming Chat.**")
             
        # Run standard Greeting
        session_id = user_id
        version = db.get_session_version(session_id)
        ver_session_id = f"{session_id}_{version}"
        
        # Send "typing"
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, agent.run, "Hi", ver_session_id)
        full_response = result[0]
        
        await context.bot.send_message(chat_id=user_id, text=full_response)

async def role_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The Master Dispatcher.
    Routes updates based on User Role (Admin vs Client).
    """
    user_id = str(update.effective_chat.id)
    admin_id = str(Config.TELEGRAM_ADMIN_CHAT_ID) if Config.TELEGRAM_ADMIN_CHAT_ID else None
    
    # 1. ADMIN LOGIC
    if admin_id and user_id == admin_id:
        # Admin is ignored by the AI Waiter.
        # We can add specific Admin commands here or just echo
        # For now, just let them know the bot is listening? 
        # Or maybe the Admin wants to test the bot too? 
        # Requirement: "The Admin must be having a different chat console"
        # So we should probably NOT run the agent for the admin.
        
        # Check if it's a command
        if update.message.text.startswith("/"):
            # Let standard command handlers deal with it
            return 
            
        # Otherwise, assume it's chat. 
        # If Admin sends text, maybe we ignore or provide a help menu?
        await context.bot.send_message(chat_id=update.effective_chat.id, text="👨‍💼 Admin Console Active.\nUsage:\n- Wait for payment alerts.\n- Click Verify/Deny buttons.")
        return

    # 2. CLIENT LOGIC (The Waiter Agent)
    await handle_message(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages (Client Side)."""
    user_text = update.message.text
    session_id = str(update.effective_chat.id)
    
    # Send "typing" action to show user we are working
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Use synchronous run() in a thread
    loop = asyncio.get_running_loop()
    
    from storage import db
    version = db.get_session_version(session_id)
    ver_session_id = f"{session_id}_{version}"
    
    result = await loop.run_in_executor(None, agent.run, user_text, ver_session_id)
    full_response, metadata = result
    
    if not full_response:
        full_response = "..."
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text=full_response)
    
    if metadata.get("reset_session"):
         db.increment_session_version(session_id)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice notes."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice support is coming soon on Telegram! Please type your message for now.")

async def approve_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command: /approve <order_id>
    Usage: /approve order_12345
    """
    # 1. Security Check
    user_id = str(update.effective_chat.id)
    admin_id = Config.TELEGRAM_ADMIN_CHAT_ID
    
    if not admin_id or user_id != str(admin_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Unauthorized access.")
        return

    # 2. Parse Code
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /approve <order_id>")
        return
        
    order_id = context.args[0]
    
    # 3. Look up Session from Order ID to notify user
    from storage import db
    rows = db.execute_query("SELECT table_id, status FROM orders WHERE order_id = ?", (order_id,))
    
    if not rows:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Order {order_id} not found.")
        return
        
    order_data = rows[0]
    stored_session_id = order_data['table_id']
    real_chat_id = stored_session_id.split('_')[0]
    current_status = order_data['status']
    
    if current_status == 'PAID':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Order {order_id} is already marked PAID.")
        return

    # 4. Trigger the Agent
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Approving Order {order_id}...")
    
    # Run agent in background thread
    loop = asyncio.get_running_loop()
    # User message injected: "SYSTEM_EVENT: ADMIN_VERIFIED"
    result = await loop.run_in_executor(None, agent.run, "SYSTEM_EVENT: ADMIN_VERIFIED", stored_session_id)
    full_response, metadata = result
    
    # 5. Notify User
    await context.bot.send_message(chat_id=real_chat_id, text=full_response)
    
    if metadata.get("reset_session"):
        from storage import db
        db.increment_session_version(real_chat_id)
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Order {order_id} marked PAID. User notified.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Client command: /reset
    Forcefully rotates the session to clear memory.
    """
    user_id = str(update.effective_chat.id)
    from storage import db
    db.increment_session_version(user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🧹 Memory wiped. Starting a fresh session.")


def build_app():
    """Factory function to create the Application instance."""
    if not Config.TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        return None

    async def post_init(application: object) -> None:
        """Explicitly initialize the bot to prevent ExtBot errors."""
        await application.bot.initialize()
        print(f"Bot Initialized: ID={application.bot.id}")

    application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).post_init(post_init).build()
    
    start_handler = CommandHandler('start', start)
    approve_handler = CommandHandler('approve', approve_payment_command)
    reset_handler = CommandHandler('reset', reset_command)
    
    application.add_handler(start_handler)
    application.add_handler(reset_handler)
    
    # 1. Admin Commands & Callbacks
    application.add_handler(CommandHandler('approve', approve_payment_command)) 
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # 2. Role Dispatcher
    dispatcher_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), role_dispatcher)
    application.add_handler(dispatcher_handler)
    
    # 3. Voice Support
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    application.add_error_handler(error_handler)
    
    return application

if __name__ == '__main__':
    application = build_app()
    if application:
        print("Telegram Bot is running...")
        application.run_polling()