import os
import json
import httpx
from app.social.base import Post

NIM_URL = os.getenv("NIM_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {NIM_API_KEY}",
    "Content-Type": "application/json"
}

async def _nim(prompt: str, max_tokens=200) -> str:
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(NIM_URL, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def interpret_command(user_text: str) -> tuple[str, list]:
    prompt = f"""You are a command parser for a social media bot. Available commands:
SCAN, LIKE <id>, COMMENT <id> <text>, COMMENT_DRAFT <id>, POST <text>, REPLY <id> <text>, SETBIO <text>, SETPIC, SOLVE <code>, STATUS.
User message: "{user_text}"
Return ONLY the command and arguments, e.g., LIKE 3, COMMENT 5 nice art!, UNKNOWN.
If the user asks to draft a comment, output COMMENT_DRAFT <id>. If they ask to see posts, output SCAN."""
    result = await _nim(prompt, max_tokens=40)
    parts = result.strip().split(maxsplit=1)
    cmd = parts[0].upper() if parts else "UNKNOWN"
    args = parts[1].split() if len(parts) > 1 else []
    return cmd, args

async def draft_comment(post_summary: str) -> str:
    prompt = f"Write a short, engaging social media comment (max 150 chars) for a post described as: '{post_summary}'. Casual tone. Only return the comment, no quotes."
    comment = await _nim(prompt, max_tokens=80)
    return comment.strip().strip('"')

async def rank_and_summarize_posts(posts: list[Post]) -> list[Post]:
    # For efficiency, batch calls; here we do one by one for simplicity
    for post in posts:
        prompt = f"""User interests: comic-books, baddies, street content.
Post caption: {post.caption[:200]}
Author: {post.author}
Hashtags: {', '.join(post.hashtags)}
Return JSON: {{"score": 0-100, "summary": "max 10 words"}}."""
        raw = await _nim(prompt, max_tokens=60)
        try:
            data = json.loads(raw)
            post.summary = data.get("summary", "")
            post.score = int(data.get("score", 50))
        except:
            post.summary = post.caption[:50]
            post.score = 50
    posts.sort(key=lambda p: p.score, reverse=True)
    return posts
