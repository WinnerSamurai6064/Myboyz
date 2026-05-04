from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Post:
    id: str
    url: str
    thumbnail_url: str
    caption: str
    author: str
    hashtags: list = field(default_factory=list)
    summary: str = ""
    score: int = 50


class SocialClient(ABC):
    @abstractmethod
    async def login(self, session: dict) -> dict: ...
    @abstractmethod
    async def search_content(self, interests: list[str], limit: int) -> list[Post]: ...
    @abstractmethod
    async def like(self, post_id: str): ...
    @abstractmethod
    async def comment(self, post_id: str, text: str): ...
    @abstractmethod
    async def create_post(self, text: str, image: bytes | None): ...
    @abstractmethod
    async def update_bio(self, text: str): ...
    @abstractmethod
    async def update_profile_pic(self, image: bytes): ...
