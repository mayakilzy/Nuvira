"""
OpenRouter wrapper — model-agnostic. Swap models by changing OPENROUTER_MODEL
in .env, no code change. This is the single AI entry point for the whole app.
"""
import httpx

from app.config import settings


class AIServiceError(Exception):
    pass


async def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    **kwargs,
) -> str:
    """Send a chat-completion request to OpenRouter and return the text reply."""
    if not settings.OPENROUTER_API_KEY:
        raise AIServiceError("OPENROUTER_API_KEY is not configured")

    payload = {
        "model": model or settings.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.FRONTEND_URL,
        "X-Title": settings.APP_NAME,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )
    if resp.status_code != 200:
        raise AIServiceError(f"OpenRouter {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]
