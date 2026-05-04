from instagrapi import Client
from app.social.base import SocialClient, Post
from app.state import save_session
import asyncio

class InstagramClient(SocialClient):
    def __init__(self, session: dict = None):
        self.client = Client()
        if session:
            self.client.set_settings(session)

    async def login(self, session: dict = None) -> dict:
        # instagrapi is not async, so run in thread
        loop = asyncio.get_running_loop()
        if session:
            self.client.set_settings(session)
            try:
                await loop.run_in_executor(None, self.client.login, "", "", verification_code="")
            except Exception:
                # full login with credentials (should be set in env)
                pass
        return self.client.get_settings()

    async def search_content(self, interests: list[str], limit=30) -> list[Post]:
        loop = asyncio.get_running_loop()
        posts = []
        for tag in interests:
            medias = await loop.run_in_executor(None, self.client.hashtag_medias_recent, tag, limit)
            for m in medias:
                posts.append(Post(
                    id=m.pk,
                    url=f"https://instagram.com/p/{m.code}",
                    thumbnail_url=m.thumbnail_url,
                    caption=m.caption_text or "",
                    author=m.user.username,
                    hashtags=[h.name for h in m.caption_hashtags] if hasattr(m, 'caption_hashtags') else []
                ))
        return posts[:limit]

    async def like(self, post_id: str):
        await asyncio.get_running_loop().run_in_executor(None, self.client.media_like, post_id)
        save_session(self.client.get_settings())

    async def comment(self, post_id: str, text: str):
        await asyncio.get_running_loop().run_in_executor(None, self.client.media_comment, post_id, text)
        save_session(self.client.get_settings())

    # Other methods (create_post, update_bio, update_profile_pic) similarly
