"""
Fix 2 — embedding scope columns are set in the SAME insert.

Two documents processed back to back must each get their own
subject_package_id / chapter_id / document_id / user_id. Verified with a
fake session that records every row passed to db.add(); the embedding
provider is mocked (no OpenAI call) and no real database is touched.
"""
import asyncio
from types import SimpleNamespace

from app.models.content import UploadedDocument
from app.models.embedding import Embedding
from app.services import document_service, embedding_service


class FakeDocQuery:
    def __init__(self, first_value):
        self._first_value = first_value

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        raise AssertionError("order_by(...) re-query (the old last() lookup) must not be used")

    def first(self):
        return self._first_value


class FakeSession:
    """Records rows added via db.add(); serves UploadedDocument lookups;
    blows up if anything re-queries the Embedding table (old last() pattern)."""

    def __init__(self, doc):
        self._doc = doc
        self.added = []
        self.commit_count = 0

    def query(self, model, *args, **kwargs):
        if model is Embedding:
            raise AssertionError("add_embedding must not re-query the Embedding table")
        assert model is UploadedDocument
        return FakeDocQuery(self._doc)

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.commit_count += 1

    def refresh(self, row):
        pass


def _doc(doc_id, pkg_id, chapter_id, user_id, filename="file.pdf"):
    return SimpleNamespace(
        id=doc_id,
        uploaded_by_user_id=user_id,
        subject_package_id=pkg_id,
        chapter_id=chapter_id,
        filename=filename,
        storage_path=f"/app/uploads/{filename}",
        status="processing",
        chunk_count=0,
        error_note=None,
    )


def _process(db, monkeypatch, text=""):
    # mock the embedding provider — never call the OpenAI API from tests
    async def fake_get_embedding(chunk_text):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(embedding_service, "get_embedding", fake_get_embedding)
    # mock text extraction so no real PDF parsing / file access happens
    monkeypatch.setattr(document_service, "extract_text", lambda path: text)
    asyncio.run(document_service.process_document(db, db._doc.id))


def test_add_embedding_sets_scope_columns_in_same_insert(monkeypatch):
    db = FakeSession(_doc(doc_id=1, pkg_id=101, chapter_id=1001, user_id=7))
    _process(db, monkeypatch, text=" ".join(f"w{i}" for i in range(50)))

    # scope already set on the inserted row — no follow-up UPDATE
    assert len(db.added) == 1
    row = db.added[0]
    assert row.subject_package_id == 101
    assert row.chapter_id == 1001
    assert row.document_id == 1
    assert row.user_id == 7
    assert db.added[0].content  # chunk text stored


def test_two_documents_back_to_back_get_correct_scope(monkeypatch):
    text = " ".join(f"w{i}" for i in range(2000))  # -> multiple chunks

    # --- document A ---
    doc_a = _doc(doc_id=1, pkg_id=101, chapter_id=1001, user_id=7, filename="a.pdf")
    db_a = FakeSession(doc_a)
    _process(db_a, monkeypatch, text=text)
    assert doc_a.status == "ready"
    assert doc_a.chunk_count == len(db_a.added) > 0
    for row in db_a.added:
        assert isinstance(row, Embedding)
        assert row.subject_package_id == 101
        assert row.chapter_id == 1001
        assert row.document_id == 1
        assert row.user_id == 7

    # --- document B, processed right after A with a different scope ---
    doc_b = _doc(doc_id=2, pkg_id=202, chapter_id=2002, user_id=8, filename="b.pdf")
    db_b = FakeSession(doc_b)
    _process(db_b, monkeypatch, text=text)
    assert doc_b.status == "ready"
    assert len(db_b.added) > 0
    for row in db_b.added:
        assert isinstance(row, Embedding)
        assert row.subject_package_id == 202
        assert row.chapter_id == 2002
        assert row.document_id == 2
        assert row.user_id == 8
