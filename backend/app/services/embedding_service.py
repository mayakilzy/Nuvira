"""Embedding generation with a production provider and an offline staging seam."""
import hashlib
import httpx

from app.config import settings


class EmbeddingServiceError(Exception):
    pass


_transient_test_failures: set[str] = set()


def _deterministic_test_embedding(text: str) -> list[float]:
    """Return a stable local vector without sending staging content externally."""
    if settings.ENV == "production":
        raise EmbeddingServiceError("The deterministic test provider is forbidden in production")
    marker = "NUVIRA_TRANSIENT_EMBEDDING_FAILURE"
    if marker in text and text not in _transient_test_failures:
        _transient_test_failures.add(text)
        raise EmbeddingServiceError("Controlled transient staging failure")
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [
        ((digest[index % len(digest)] / 255.0) * 2.0) - 1.0
        for index in range(settings.EMBEDDING_DIM)
    ]


async def get_embedding(text: str) -> list[float]:
    if settings.EMBEDDING_PROVIDER == "deterministic-test":
        return _deterministic_test_embedding(text)
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
