import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# logic from config.py to get key
api_key = os.getenv("GROQ_API_KEY", "")
api_keys = os.getenv("GROQ_API_KEYS", "").split(",") if os.getenv("GROQ_API_KEYS") else []

if "," in api_key:
    extra = api_key.split(",")
    api_key = extra[0]

if not api_key and api_keys:
    api_key = api_keys[0]

if not api_key:
    print("No GROQ_API_KEY found.")
    exit(1)

client = Groq(api_key=api_key.strip())

try:
    print(f"Using key starting with: {api_key.strip()[:4]}...")
    models = client.models.list()
    print("\nAvailable Groq Models:")
    for m in models.data:
        print(f"- {m.id}")
except Exception as e:
    print(f"Error: {e}")
