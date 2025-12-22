import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from agents.smart_waiter_agent import SmartWaiterAgent
from storage.supabase_memory import SmartWaiterMemory

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

# Global Session Store REPLACED by Supabase Memory
# session_store was {user_id: {"cart": [], "lang": "English"}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    # Show Session Choice Options (Legacy) or Language Options?
    # User flow: Start -> Language -> Session Mode? 
    # Let's combine. 
    
    keyboard = [
        [
            InlineKeyboardButton("English 🇺🇸", callback_data='lang_English'),
            InlineKeyboardButton("Français 🇫🇷", callback_data='lang_French'),
        ],
        [
            InlineKeyboardButton("Hausa 🇳🇬", callback_data='lang_Hausa'),
            InlineKeyboardButton("Yoruba 🇳🇬", callback_data='lang_Yoruba'),
            InlineKeyboardButton("Igbo 🇳🇬", callback_data='lang_Igbo'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="👋 Welcome to Smart Waiter!\nPlease select your preferred language:",
        reply_markup=reply_markup
    )

async def view_cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cart command or button."""
    user_id = update.effective_chat.id
    
    # Fetch from Supabase
    state = SmartWaiterMemory.get_state(user_id)
    # DB field is 'cart_data', not 'cart'
    items = state.get("cart_data", [])
    
    if not items:
        await context.bot.send_message(chat_id=user_id, text="Your cart is empty! 🛒\nUse /menu to add items.")
        return

    receipt = "<b>📝 Your Order Summary:</b>\n\n"
    total = 0
    for idx, obj in enumerate(items, 1):
        receipt += f"{idx}. {obj['item']} — ₦{obj['price']:,.0f}\n"
        total += obj['price']
    
    receipt += f"\n<b>💰 Total: ₦{total:,.0f}</b>"
    
    keyboard = [
        [InlineKeyboardButton("✅ Checkout & Pay", callback_data="checkout")],
        [InlineKeyboardButton("❌ Clear Cart", callback_data="clear_cart")]
    ]
    
    await context.bot.send_message(
        chat_id=user_id, 
        text=receipt, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="HTML"
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactions with Inline Buttons."""
    query = update.callback_query
    # await query.answer() # Moving answer down to handle specific alerts
    
    print(f"DEBUG: Callback received: {query.data}")
    
    data = query.data
    if not data: return
        
    parts = data.split("_")
    action = parts[0]
    
    # --- CART ACTIONS ---
    # --- CART ACTIONS ---
    if action == "checkout":
        await query.answer()
        user_id = update.effective_chat.id
        
        # Supabase Fetch
        state = SmartWaiterMemory.get_state(user_id)
        items = state.get("cart_data", [])
        
        if not items:
            await query.edit_message_text(text="Cart is empty.")
            return
            
        # STATLESS MATH: Calculate total here
        total = sum(item['price'] for item in items)
        lang = state.get("selected_language", "English")
        
        # 1. Notify Admin (Simulated)
        if Config.TELEGRAM_ADMIN_CHAT_ID:
             pass
             
        # 2. Trigger Agent Payment Flow
        # INJECT THE TRUTH: Tell the AI exactly what the total is.
        from storage import db
        version = db.get_session_version(str(user_id))
        ver_session_id = f"{user_id}_{version}"
        
        # Immediate feedback
        await query.edit_message_text(text=f"✅ Checkout initiated for ₦{total:,.0f}.\nProcessing your request...")
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        
        # Inject Context into Agent run
        context_data = {
            "language": lang,
            "cart_total": total
        }
        
        loop = asyncio.get_running_loop()
        command_text = f"I want to pay. My total is {total}."
        
        result = await loop.run_in_executor(
            None, 
            lambda: agent.run(command_text, ver_session_id, context_data=context_data)
        )
        full_response, metadata = result
        
        # Clear Cart after SUCCESSFUL handover (or should we wait for payment success?)
        SmartWaiterMemory.update_cart(user_id, [])
        
        if full_response:
             await context.bot.send_message(chat_id=user_id, text=full_response)
        return

    elif action == "clear":
        # clear_cart
        if parts[1] == "cart":
            await query.answer()
            user_id = update.effective_chat.id
            SmartWaiterMemory.update_cart(user_id, [])
            await query.edit_message_text(text="🗑️ Cart cleared.")
            return

    elif action == "lang":
        await query.answer()
        selected_lang = parts[1]
        user_id = update.effective_chat.id # Pass Int to Supabase
        
        # Lock in Supabase
        SmartWaiterMemory.update_language(user_id, selected_lang)
        
        # Lock in Legacy DB (Redundancy)
        from storage import db
        db.set_user_pref(str(user_id), language=selected_lang)
        
        # Confirm to User
        # "Language locked! I will now respond in [LANG]. Type /reset to change."
        await query.edit_message_text(text=f"✅ Language set to **{selected_lang}**.\n(Type /reset to change anytime).")
        
        # Trigger Agent Greeting Immediately
        session_id = user_id
        version = db.get_session_version(session_id)
        ver_session_id = f"{session_id}_{version}"
        
        # Send "typing"
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        
        loop = asyncio.get_running_loop()
        # Send a dummy "Hi" or just let the agent know we started? 
        # If we send "Hi", the agent will skip onboarding (since lang is set) and greet.
        result = await loop.run_in_executor(None, agent.run, "Hi", ver_session_id)
        full_response, metadata = result
        
        if full_response:
             await context.bot.send_message(chat_id=user_id, text=full_response)
        return

    # --- MENU NAVIGATION ---
    elif action == "show":
        await query.answer()
        # show_cat_CategoryName
        if len(parts) < 3 or parts[1] != "cat": return
        category_name = parts[2]
        
        from tools import menu_ops
        items = menu_ops.get_category_items(category_name)
        
        keyboard = []
        for item, price in items.items():
            # Button for each item: add_ItemName_Price
            # Careful with spaces in item names, callback data limit is 64 bytes.
            # Using clean separator.
            keyboard.append([InlineKeyboardButton(f"{item} - ₦{price:,.0f}", callback_data=f"add_{item}_{price}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Fix: Category name might need decoding or just raw string use
        await query.edit_message_text(text=f"📂 **{category_name}**", reply_markup=reply_markup)
        
    elif action == "main":
        await query.answer()
        # main_menu
        if parts[1] == "menu":
             from tools import menu_ops
             categories = menu_ops.get_categories()
             
             keyboard = []
             for i in range(0, len(categories), 2):
                row = [InlineKeyboardButton(cat, callback_data=f"show_cat_{cat}") for cat in categories[i:i+2]]
                keyboard.append(row)
             
             # Add View Cart Button
             keyboard.append([InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")])

             reply_markup = InlineKeyboardMarkup(keyboard)
             await query.edit_message_text(text="🍽️ **Evolution Lounge Menu**\nSelect a category:", reply_markup=reply_markup)

    elif action == "view":
        # view_cart
        if parts[1] == "cart":
             await query.answer()
             # Re-use the command logic but context is different (CallbackQuery)
             # Easier to just call the function but we need to supply 'update' which has 'message' ...
             # Actually, let's just copy logic or separate function.
             user_id = update.effective_chat.id
             items = cart_store.get(user_id, [])
             
             if not items:
                await query.edit_message_text(text="Your cart is empty! 🛒\nUse /menu to add items.")
                return

             receipt = "<b>📝 Your Order Summary:</b>\n\n"
             total = 0
             for idx, obj in enumerate(items, 1):
                receipt += f"{idx}. {obj['item']} — ₦{obj['price']:,.0f}\n"
                total += obj['price']
            
             receipt += f"\n<b>💰 Total: ₦{total:,.0f}</b>"
             
             keyboard = [
                [InlineKeyboardButton("✅ Checkout & Pay", callback_data="checkout")],
                [InlineKeyboardButton("❌ Clear Cart", callback_data="clear_cart")]
             ]
             # Send new message or edit? Edit is cleaner.
             await query.edit_message_text(text=receipt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif action == "add":
        # add_ItemName_Price
        # parts: 0=add, 1=ItemName, 2=Price (maybe more if item has spaces? No, split by _ is dangerous if item has _)
        # WE SHOULD JOIN back the parts
        # Safer parsing:
        
        # Re-construct data string
        full_data = query.data # add_Item Name_Price
        # remove prefix "add_"
        content = full_data[4:]
        # Split by last underscore to get price? 
        # Assuming Item Name doesn't have underscores? Or we just take everything before last _
        last_underscore = content.rfind('_')
        item_name = content[:last_underscore]
        price_str = content[last_underscore+1:]
        price = 0
        try:
            price = int(float(price_str))
        except ValueError:
            logger.error(f"Could not parse price '{price_str}' for item '{item_name}'")
            pass
        
        user_id = update.effective_chat.id
        
        # ADD TO SUPABASE
        state = SmartWaiterMemory.get_state(user_id)
        current_cart = state.get("cart_data", [])
        current_cart.append({"item": item_name, "price": price})
        
        SmartWaiterMemory.update_cart(user_id, current_cart)
        
        # Notify User (Popup)
        await query.answer(f"✅ Added {item_name} to cart!", show_alert=False)
        
        # Sync with Agent by injecting a message
        from storage import db
        # We need session ID
        version = db.get_session_version(str(user_id))
        ver_session_id = f"{user_id}_{version}"
        
        loop = asyncio.get_running_loop()
        # Inject "Add <Item>" command
        # This forces the agent to process the order
        command_text = f"Add {item_name}"
        result = await loop.run_in_executor(None, agent.run, command_text, ver_session_id)
        full_response, metadata = result
        
        # Send agent response as a regular message (e.g. "Added White Rice to your order. Anything else?")
        if full_response:
             await context.bot.send_message(chat_id=user_id, text=full_response)
        return

    # order_id check for admin actions
    if len(parts) > 1:
        order_id = parts[1]
    
    # --- ADMIN ACTIONS ---
    if action in ["approve", "deny"]:
        await query.answer()
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
        await query.answer()
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

    # --- CLIENT SESSION ACTIONS (Legacy/Optional now that we have Lang buttons) ---
    elif action == "session":
        await query.answer()
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
    """Handle incoming text messages (Client Side) with Supabase State Lock."""
    user_text = update.message.text
    user_id = update.effective_chat.id
    session_id = str(user_id)
    
    # 1. Supabase State
    state = SmartWaiterMemory.get_state(user_id)
    
    # 2. Calculate Truth
    cart_items = state.get("cart_data", [])
    current_total = sum(item['price'] for item in cart_items)
    
    # NOTE: Our DB column is 'selected_language', but agent expects 'language'
    current_lang = state.get("selected_language", "English")
    
    # 3. Inject Context
    context_data = {
        "language": current_lang,
        "cart_total": current_total,
        "cart_items_count": len(cart_items)
    }
    
    # Send "typing"
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    
    loop = asyncio.get_running_loop()
    
    from storage import db
    version = db.get_session_version(session_id)
    ver_session_id = f"{session_id}_{version}"
    
    # Run agent with context
    result = await loop.run_in_executor(
        None, 
        lambda: agent.run(user_text, ver_session_id, context_data=context_data)
    )
    full_response, metadata = result
    
    if not full_response:
        full_response = "..."
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text=full_response)
    
    if metadata.get("reset_session"):
         db.increment_session_version(session_id)
         SmartWaiterMemory.update_cart(user_id, [])

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
    user_id = update.effective_chat.id
    from storage import db
    db.increment_session_version(str(user_id))
    # Clear Brain
    SmartWaiterMemory.update_cart(user_id, [])
    await context.bot.send_message(chat_id=user_id, text="🧹 Memory wiped. Starting a fresh session.")


async def show_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command to show hierarchical menu."""
    from tools import menu_ops
    categories = menu_ops.get_categories()
    
    keyboard = []
    # Create rows of 2 buttons for a professional look
    for i in range(0, len(categories), 2):
        row = [InlineKeyboardButton(cat, callback_data=f"show_cat_{cat}") for cat in categories[i:i+2]]
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🍽️ **Evolution Lounge Menu**\nPlease select a category:", 
        reply_markup=reply_markup
    )

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
    menu_handler = CommandHandler('menu', show_menu_command)
    cart_handler = CommandHandler('cart', view_cart_command)
    
    application.add_handler(start_handler)
    application.add_handler(reset_handler)
    application.add_handler(menu_handler)
    application.add_handler(cart_handler)
    
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