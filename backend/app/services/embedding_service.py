"""
Embedding generation — via OpenAI (text-embedding-3-small, dim=1536, matches
settings.EMBEDDING_DIM). Separate API key from OPENROUTER_API_KEY, because
OpenRouter does not serve embeddings.
"""
import httpx

from app.config import settings


class EmbeddingServiceError(Exception):
    pass


async def get_embedding(text: str) -> list[float]:
    if not settings.OPENAI_API_KEY:
        raise EmbeddingServiceError("OPENAI_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": "text-embedding-3-small", "input": text},
        )
    if resp.status_code != 200:
        raise EmbeddingServiceError(f"OpenAI {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return data["data"][0]["embedding"]
