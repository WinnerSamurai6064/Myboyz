import os
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.shared import active_windows          # ← changed
from app.nim import interpret_command, draft_comment
from app.social.instagram import InstagramClient
from app.state import load_session

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

bot_instance = Application.builder().token(TELEGRAM_TOKEN).build()

social = None

def get_social():
    global social
    if social is None:
        session = load_session()
        social = InstagramClient(session)
    return social

# … keep all handlers the same (start, handle_message, button_callback, execute_command, confirm_handler) …

def setup_bot():
    # … keep the same handler registration …
    return bot_instance
