import asyncio, time, os
from app.bot import bot_instance, get_social, ADMIN_CHAT_ID
from app.nim import rank_and_summarize_posts
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

ACTIVE_WINDOW_SECONDS = int(os.getenv("ACTIVE_WINDOW_SECONDS", "300"))
active_windows = []


class ActiveWindow:
    def __init__(self):
        self.start_time = time.time()
        self.user_responded = False
        self.original_posts = []
        self.task = asyncio.create_task(self._run())

    async def _run(self):
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
        raw = await soc.search_content(
            ["comicbooks", "baddies", "streetwear"], limit=30
        )
        self.original_posts = raw
        if raw:
            ranked = await rank_and_summarize_posts(raw)
            top = ranked[:10]
            await _send_card(top)

    async def auto_like(self):
        soc = get_social()
        to_like = (self.original_posts or [])[:3]
        for p in to_like:
            await soc.like(p.id)
        await bot_instance.bot.send_message(
            ADMIN_CHAT_ID, f"🤖 Auto‑liked {len(to_like)} posts."
        )


async def start_active_window():
    window = ActiveWindow()
    active_windows.append(window)


async def _send_card(posts):
    for post in posts:
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❤️ Like", callback_data=f"like_{post.id}"),
                InlineKeyboardButton("✏️ Draft", callback_data=f"commentdraft_{post.id}")
            ]
        ])
        caption = f"📌 {post.summary}\n🔗 {post.url}"
        await bot_instance.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=post.thumbnail_url,
            caption=caption,
            reply_markup=kb
        )
