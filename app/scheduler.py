import asyncio, time, os
from app.bot import bot_instance, get_social, ADMIN_CHAT_ID
from app.nim import rank_and_summarize_posts
from app.shared import active_windows          # ← changed
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# … rest of the file stays identical …
