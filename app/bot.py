import os
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.scheduler import active_windows, user_responded
from app.nim import interpret_command, draft_comment
from app.social.instagram import InstagramClient
from app.state import load_session

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Store in env

# Global bot application
bot_instance = Application.builder().token(TELEGRAM_TOKEN).build()

# Social clients (lazy init)
social = None

def get_social():
    global social
    if social is None:
        session = load_session()
        social = InstagramClient(session)
    return social

# --------- Command Handlers ---------
async def start(update, context):
    await update.message.reply_text(
        "Nemoclaw awake. Use natural language or commands like /scan, /like <id>, /comment <id> <text>."
    )

async def handle_message(update, context):
    """All text messages go through NIM to parse intent."""
    user_text = update.message.text
    command, args = await interpret_command(user_text)
    if command == "UNKNOWN":
        await update.message.reply_text("I didn't understand. Try /help.")
        return
    # Mark user responded if within an active window
    for window in active_windows:
        window.user_responded = True
    await execute_command(update, context, command, args)

async def button_callback(update, context):
    """Handle inline keyboard button presses from content cards."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("like_"):
        post_id = data.split("_")[1]
        await execute_command(update, context, "LIKE", [post_id])
    elif data.startswith("commentdraft_"):
        post_id = data.split("_")[1]
        # Generate draft comment via NIM
        # post info stored in context (simplified)
        post_summary = context.user_data.get(f"post_{post_id}", "this post")
        draft = await draft_comment(post_summary)
        await query.message.reply_text(
            f"Draft comment for post {post_id}: \"{draft}\"\n"
            f"Reply with: /comment {post_id} {draft}"
        )
    await query.edit_message_reply_markup(reply_markup=None)

async def execute_command(update, context, cmd: str, args: list):
    soc = get_social()
    if cmd == "SCAN":
        # manual scan (without auto-like)
        posts = await soc.search_content(["comicbooks", "baddies", "streetwear"])
        # ... simplified; would send content card
    elif cmd == "LIKE":
        post_id = args[0]
        await soc.like(post_id)
        await update.message.reply_text(f"Liked post {post_id}")
    elif cmd == "COMMENT":
        post_id, *text = args
        comment_text = " ".join(text)
        # Ask confirmation
        context.user_data["pending_action"] = {
            "type": "comment",
            "post_id": post_id,
            "text": comment_text
        }
        await update.message.reply_text(f"Comment: '{comment_text}' on post {post_id}. Confirm? (yes/no)")
    elif cmd == "COMMENT_DRAFT":
        post_id = args[0]
        post_summary = context.user_data.get(f"post_{post_id}", "a post")
        draft = await draft_comment(post_summary)
        context.user_data["pending_action"] = {
            "type": "comment",
            "post_id": post_id,
            "text": draft
        }
        await update.message.reply_text(f"Draft: '{draft}'. Confirm? (yes/no)")
    elif cmd == "CONFIRM":
        action = context.user_data.get("pending_action")
        if action and action["type"] == "comment":
            await soc.comment(action["post_id"], action["text"])
            await update.message.reply_text("Comment posted ✅")
            context.user_data.pop("pending_action")
    # ... other commands (POST, REPLY, SETBIO, SETPIC) follow same pattern

async def confirm_handler(update, context):
    """Handle yes/no replies for confirmation."""
    text = update.message.text.lower()
    if text in ("yes", "y"):
        await execute_command(update, context, "CONFIRM", [])
    elif text in ("no", "n"):
        context.user_data.pop("pending_action", None)
        await update.message.reply_text("Cancelled.")

# --------- Setup ---------
def setup_bot():
    bot_instance.add_handler(CommandHandler("start", start))
    bot_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_instance.add_handler(MessageHandler(filters.Regex(r'^(?i)(yes|no|y|n)$'), confirm_handler))
    bot_instance.add_handler(CallbackQueryHandler(button_callback))
    return bot_instance
