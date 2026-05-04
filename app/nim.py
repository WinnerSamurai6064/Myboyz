"""
NVIDIA NIM API wrapper for Nemoclaw.

Uses two models:
  • Kimi K2.5  (moonshotai/kimi-k2.5)  — content ranking, summarisation
  • GLM         (z-ai/glm4.7 or z-ai/glm5) — command parsing, drafting

Both are free via NVIDIA NIM (40 RPM limit, no credit card required).
"""

import os, json, httpx
from app.social.base import Post

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NIM_BASE_URL = os.getenv(
    "NIM_BASE_URL",
    "https://integrate.api.nvidia.com/v1"
)
NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")

# Model IDs – can be overridden via env
NIM_MODEL_KIMI = os.getenv("NIM_MODEL_KIMI", "moonshotai/kimi-k2.5")
NIM_MODEL_GLM  = os.getenv("NIM_MODEL_GLM",  "z-ai/glm4.7")

# Shared HTTP headers
HEADERS = {
    "Authorization": f"Bearer {NIM_API_KEY}",
    "Content-Type": "application/json",
}

# ---------------------------------------------------------------------------
# Low‑level NIM call
# ---------------------------------------------------------------------------
async def _nim(model: str, system: str, prompt: str,
               temperature: float = 0.3, max_tokens: int = 300) -> str:
    """Send a chat completion to the NVIDIA NIM API and return the text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{NIM_BASE_URL}/chat/completions",
            json=payload,
            headers=HEADERS,
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Task‑specific functions
# ---------------------------------------------------------------------------

async def interpret_command(user_text: str) -> tuple[str, list]:
    """
    Parse a natural‑language message into a structured command.

    Uses **GLM** (z-ai/glm4.7) because of its strong reasoning and
    instruction‑following abilities.
    """
    system = (
        "You are a rigid command parser for a social‑media bot. "
        "Available commands: SCAN, LIKE <id>, COMMENT <id> <text>, "
        "COMMENT_DRAFT <id>, POST <text>, REPLY <id> <text>, "
        "SETBIO <text>, SETPIC, SOLVE <code>, STATUS.\n"
        "Rules:\n"
        "- If the user asks to see or scan content → SCAN\n"
        "- If they ask to draft a comment → COMMENT_DRAFT <id>\n"
        "- If they confirm (yes/y) → CONFIRM\n"
        "- Otherwise map to the closest command.\n"
        "Return ONLY '<COMMAND> <args>'. No explanation."
    )
    raw = await _nim(NIM_MODEL_GLM, system, user_text, temperature=0.1, max_tokens=50)
    parts = raw.strip().split(maxsplit=1)
    cmd = parts[0].upper() if parts else "UNKNOWN"
    args = parts[1].split() if len(parts) > 1 else []
    return cmd, args


async def draft_comment(post_summary: str) -> str:
    """
    Generate a short, engaging comment for a post.

    Uses **GLM** – fast and good at following tone/style constraints.
    """
    system = (
        "You are a social‑media assistant. Write a short, engaging comment "
        "(max 150 characters). Casual, friendly tone. No hashtags, no emoji "
        "spam. Return ONLY the comment text, no quotes."
    )
    comment = await _nim(NIM_MODEL_GLM, system, post_summary, temperature=0.8, max_tokens=80)
    return comment.strip().strip('"')


async def rank_and_summarize_posts(posts: list[Post]) -> list[Post]:
    """
    Rank posts by relevance and generate one‑line summaries.

    Uses **Kimi K2.5** because of its strong multimodal understanding
    and large context — perfect for evaluating social‑media content.
    """
    system = (
        "You are a social‑media curator. The user is interested in: "
        "comic‑books, baddies (fashion/models), street content.\n"
        "For each post, return a JSON object: "
        '{"score": 0-100, "summary": "max 10 words"}.\n'
        "Score higher for posts that match the niches above."
    )

    for post in posts:
        prompt = (
            f"Caption: {post.caption[:150]}\n"
            f"Author: {post.author}\n"
            f"Hashtags: {', '.join(post.hashtags[:10])}"
        )
        try:
            raw = await _nim(NIM_MODEL_KIMI, system, prompt, temperature=0.3, max_tokens=80)
            data = json.loads(raw)
            post.summary = data.get("summary", post.caption[:50])
            post.score = int(data.get("score", 50))
        except Exception:
            post.summary = post.caption[:50]
            post.score = 50

    posts.sort(key=lambda p: p.score, reverse=True)
    return posts


async def generate_blog_idea(topic: str = "") -> str:
    """
    (Optional) Brainstorm a mini‑blog idea.
    Uses **Kimi K2.5** for creative generation.
    """
    system = "You are a creative social‑media assistant. Suggest a short, punchy mini‑blog post idea (2-3 sentences)."
    prompt = topic or "Give me a mini‑blog idea related to comic books, street style, or pop culture."
    return await _nim(NIM_MODEL_KIMI, system, prompt, temperature=0.9, max_tokens=150)
