import asyncio
import time
import os
from app.bot import bot_instance, get_social, ADMIN_CHAT_ID
from app.nim import rank_and_summarize_posts

ACTIVE_WINDOW_SECONDS = int(os.getenv("ACTIVE_WINDOW_SECONDS", "300"))
active_windows = []  # list to track current window objects

class ActiveWindow:
    def __init__(self):
        self.start_time = time.time()
        self.user_responded = False
        self.task = asyncio.create_task(self._run_window())

    async def _run_window(self):
        await self.scan_and_notify()
        try:
            await asyncio.sleep(ACTIVE_WINDOW_SECONDS)
            if not self.user_responded:
                await self.auto_like()
        except asyncio.CancelledError:
            pass
        finally:
            active_windows.remove(self)

    async def scan_and_notify(self):
        soc = get_social()
        raw_posts = await soc.search_content(["comicbooks", "baddies", "streetwear"], limit=30)
        # Use NIM to rank and summarize
        if raw_posts:
            ranked = await rank_and_summarize_posts(raw_posts)
            # Take top 10
            top_posts = ranked[:10]
            await send_content_card(top_posts)

    async def auto_like(self):
        soc = get_social()
        # Like up to 3 posts from niche (simplified: just first 3 from original scan)
        posts_to_like = (self.original_posts or [])[:3]
        for p in posts_to_like:
            await soc.like(p.id)
        await bot_instance.bot.send_message(ADMIN_CHAT_ID, f"Auto-liked {len(posts_to_like)} posts.")

async def start_active_window():
    window = ActiveWindow()
    active_windows.append(window)

async def send_content_card(posts):
    """Construct a Telegram message with inline keyboard for each post."""
    for post in posts:
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Like", callback_data=f"like_{post.id}"),
             InlineKeyboardButton("Draft Comment", callback_data=f"commentdraft_{post.id}")]
        ])
        caption = f"📌 {post.summary}\n🔗 [Link]({post.url})"
        await bot_instance.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=post.thumbnail_url,
            caption=caption,
            reply_markup=inline_keyboard
        )
