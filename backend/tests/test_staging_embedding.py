import asyncio

import pytest

from app.config import Settings, settings
from app.services import embedding_service


def test_deterministic_staging_embeddings_are_local_stable_and_sized(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "deterministic-test")
    first = asyncio.run(embedding_service.get_embedding("synthetic chemistry material"))
    second = asyncio.run(embedding_service.get_embedding("synthetic chemistry material"))
    different = asyncio.run(embedding_service.get_embedding("different synthetic material"))
    assert first == second
    assert first != different
    assert len(first) == settings.EMBEDDING_DIM
    assert all(-1.0 <= value <= 1.0 for value in first)


def test_deterministic_embedding_provider_is_rejected_in_production():
    with pytest.raises(ValueError, match="production must use the openai embedding provider"):
        Settings(
            ENV="production",
            DEBUG=False,
            JWT_SECRET="p" * 64,
            EMBEDDING_PROVIDER="deterministic-test",
        )
