import asyncio
from instagrapi import Client
from app.social.base import SocialClient, Post
from app.state import save_session


class InstagramClient(SocialClient):
    def __init__(self, session: dict = None):
        self.client = Client()
        if session:
            self.client.set_settings(session)

    async def login(self, session: dict = None) -> dict:
        loop = asyncio.get_running_loop()
        if session:
            self.client.set_settings(session)
            try:
                await loop.run_in_executor(None, self.client.login, "", "")
            except Exception:
                pass  # will need user to re-auth
        return self.client.get_settings()

    async def search_content(self, interests: list[str], limit=30) -> list[Post]:
        loop = asyncio.get_running_loop()
        posts = []
        for tag in interests:
            try:
                medias = await loop.run_in_executor(
                    None, self.client.hashtag_medias_recent, tag, limit
                )
                for m in medias:
                    posts.append(Post(
                        id=str(m.pk),
                        url=f"https://instagram.com/p/{m.code}",
                        thumbnail_url=str(m.thumbnail_url),
                        caption=(m.caption_text or "")[:200],
                        author=str(m.user.username),
                        hashtags=[h.name for h in getattr(m, 'caption_hashtags', [])]
                    ))
            except Exception:
                continue
        return posts[:limit]

    async def like(self, post_id: str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.client.media_like, post_id)
        save_session(self.client.get_settings())

    async def comment(self, post_id: str, text: str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.client.media_comment, post_id, text)
        save_session(self.client.get_settings())

    async def create_post(self, text: str, image: bytes | None):
        loop = asyncio.get_running_loop()
        if image:
            await loop.run_in_executor(None, self.client.photo_upload, image, text)
        else:
            await loop.run_in_executor(None, self.client.account_story, text)
        save_session(self.client.get_settings())

    async def update_bio(self, text: str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.client.account_edit, text)
        save_session(self.client.get_settings())

    async def update_profile_pic(self, image: bytes):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.client.account_change_picture, image)
        save_session(self.client.get_settings())
