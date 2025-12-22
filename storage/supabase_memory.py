from supabase import create_client
import os
import logging

logger = logging.getLogger(__name__)

# Fallback mechanism if credentials are missing (for local testing without keys)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")

class SmartWaiterMemory:
    @staticmethod
    def get_state(user_id):
        """Fetch language and cart from the database."""
        if not supabase:
            # Fallback for dev without keys or if init failed
            logger.warning("Supabase not set up. Using temporary RAM dict.")
            return {"user_id": user_id, "selected_language": "English", "cart_data": []}
            
        try:
            # Note: user_id in telegram is BigInt, but we might store as string or bigint.
            # If table is bigint, pass int. 
            res = supabase.table("user_sessions").select("*").eq("user_id", user_id).execute()
            if not res.data:
                # Create a new session if this is a first-time user
                new_data = {"user_id": user_id, "selected_language": "English", "cart_data": []}
                supabase.table("user_sessions").insert(new_data).execute()
                return new_data
            return res.data[0]
        except Exception as e:
            logger.error(f"Supabase Error getting state: {e}")
            # Fail safe
            return {"user_id": user_id, "selected_language": "English", "cart_data": []}

    @staticmethod
    def update_language(user_id, lang_code):
        """Lock the language choice permanently."""
        if not supabase: return
        try:
            supabase.table("user_sessions").update({"selected_language": lang_code}).eq("user_id", user_id).execute()
        except Exception as e:
            logger.error(f"Supabase Error updating language: {e}")

    @staticmethod
    def update_cart(user_id, new_cart):
        """Save the updated cart items."""
        if not supabase: return
        try:
            # Postgres JSONB accepts list of dicts directly
            supabase.table("user_sessions").update({"cart_data": new_cart}).eq("user_id", user_id).execute()
        except Exception as e:
            logger.error(f"Supabase Error updating cart: {e}")
