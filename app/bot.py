import os
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.scheduler import active_windows
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


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------
async def start(update, context):
    await update.message.reply_text(
        "🦞 Nemoclaw awake.\n"
        "Models: Kimi K2.5 + GLM via NVIDIA NIM (free tier, 40 RPM)\n"
        "Speak naturally, or use /scan, /like <id>, /comment <id> <text>."
    )


async def handle_message(update, context):
    user_text = update.message.text
    # NIM command parser (GLM by default – configurable)
    command, args = await interpret_command(user_text)

    if command == "UNKNOWN":
        await update.message.reply_text("I didn't understand. Try /help.")
        return

    for window in active_windows:
        window.user_responded = True

    await execute_command(update, context, command, args)


async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("like_"):
        post_id = data.split("_")[1]
        await execute_command(update, context, "LIKE", [post_id])
    elif data.startswith("commentdraft_"):
        post_id = data.split("_")[1]
        summary = context.user_data.get(f"post_{post_id}", "this post")
        draft = await draft_comment(summary)
        await query.message.reply_text(
            f"Draft for post {post_id}:\n「{draft}」\n"
            f"Reply: /comment {post_id} {draft}"
        )
    await query.edit_message_reply_markup(reply_markup=None)


async def execute_command(update, context, cmd: str, args: list):
    soc = get_social()

    if cmd == "SCAN":
        posts = await soc.search_content(["comicbooks", "baddies", "streetwear"])
        await update.message.reply_text(f"Scanned {len(posts)} posts. Use /top to see them.")

    elif cmd == "LIKE":
        pid = args[0]
        await soc.like(pid)
        await update.message.reply_text(f"❤️ Liked post {pid}")

    elif cmd == "COMMENT":
        post_id, *text = args
        comment_text = " ".join(text)
        context.user_data["pending_action"] = {
            "type": "comment", "post_id": post_id, "text": comment_text
        }
        await update.message.reply_text(
            f"Comment: 「{comment_text}」 on post {post_id}\nConfirm? (yes/no)"
        )

    elif cmd == "COMMENT_DRAFT":
        post_id = args[0]
        summary = context.user_data.get(f"post_{post_id}", "a post")
        draft = await draft_comment(summary)
        context.user_data["pending_action"] = {
            "type": "comment", "post_id": post_id, "text": draft
        }
        await update.message.reply_text(f"Draft: 「{draft}」\nConfirm? (yes/no)")

    elif cmd == "CONFIRM":
        action = context.user_data.get("pending_action")
        if action and action["type"] == "comment":
            await soc.comment(action["post_id"], action["text"])
            await update.message.reply_text("✅ Comment posted")
            context.user_data.pop("pending_action", None)

    elif cmd == "POST":
        text = " ".join(args)
        context.user_data["pending_action"] = {"type": "post", "text": text}
        await update.message.reply_text(f"Post: 「{text}」\nConfirm? (yes/no)")

    elif cmd == "STATUS":
        await update.message.reply_text(
            "🦞 Nemoclaw running\n"
            f"Active windows: {len(active_windows)}\n"
            "Models: Kimi K2.5 + GLM via NVIDIA NIM"
        )


async def confirm_handler(update, context):
    text = update.message.text.lower()
    if text in ("yes", "y"):
        await execute_command(update, context, "CONFIRM", [])
    elif text in ("no", "n"):
        context.user_data.pop("pending_action", None)
        await update.message.reply_text("Cancelled.")


# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------
def setup_bot():
    bot_instance.add_handler(CommandHandler("start", start))
    bot_instance.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^(?i)(yes|no|y|n)$'),
        handle_message
    ))
    bot_instance.add_handler(MessageHandler(
        filters.Regex(r'^(?i)(yes|no|y|n)$'), confirm_handler
    ))
    bot_instance.add_handler(CallbackQueryHandler(button_callback))
    return bot_instance
