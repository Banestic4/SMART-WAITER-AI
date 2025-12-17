#!/bin/bash
# Ensure data directory exists (auto-created by disk mount usually, but safety first)
mkdir -p data

# Run migrations (safe to run multiple times)
python migrate_db.py

# Start the Bot
python telegram_bot.py
