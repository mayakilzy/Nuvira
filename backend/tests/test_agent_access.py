"""Authorization regression tests for the educational API surface."""
import pytest

from app.core.security import create_access_token, hash_password
from app.models.content import Chapter, UploadedDocument
from app.models.preferences import UserPreferences
from app.models.study import AvatarState, PhraseUsage, StudyLog
from app.models.subject import Concept, SubjectPackage, UserSubjectAccess
from app.models.user import User
from tests.conftest import TestingSessionLocal, engine


EDUCATION_TABLES = [
    UserPreferences,
    AvatarState,
    PhraseUsage,
    StudyLog,
    UploadedDocument,
    Chapter,
    Concept,
    UserSubjectAccess,
    SubjectPackage,
]


@pytest.fixture(autouse=True)
def education_schema():
    for model in reversed(EDUCATION_TABLES):
        model.__table__.drop(engine, checkfirst=True)
    for model in EDUCATION_TABLES:
        model.__table__.create(engine, checkfirst=True)
    yield


def _seed():
    db = TestingSessionLocal()
    owner = User(email="owner@example.com", password_hash=hash_password("password123"))
    outsider = User(email="outsider@example.com", password_hash=hash_password("password123"))
    db.add_all([owner, outsider])
    db.flush()
    subject = SubjectPackage(name="Organic Chemistry", language="de")
    db.add(subject)
    db.flush()
    db.add(UserSubjectAccess(user_id=owner.id, subject_package_id=subject.id))
    chapter = Chapter(subject_package_id=subject.id, chapter_number=1, title="Alkanes")
    concept = Concept(subject_package_id=subject.id, name="SN2", mechanism_json={"steps": ["Attack"]})
    db.add_all([chapter, concept])
    db.commit()
    result = owner.id, outsider.id, subject.id, chapter.id, concept.id
    db.close()
    return result


def _headers(user_id: int):
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def test_subject_and_learning_content_are_scoped_to_enrollment(client):
    owner_id, outsider_id, subject_id, chapter_id, concept_id = _seed()

    subjects = client.get("/agent/subjects", headers=_headers(owner_id))
    assert subjects.status_code == 200
    assert [item["id"] for item in subjects.json()["subjects"]] == [subject_id]

    chapters = client.get(
        "/agent/chapters",
        params={"subject_package_id": subject_id},
        headers=_headers(owner_id),
    )
    assert chapters.status_code == 200
    assert chapters.json()["chapters"][0]["id"] == chapter_id

    concepts = client.get(
        "/agent/concepts",
        params={"subject_package_id": subject_id, "chapter_id": chapter_id},
        headers=_headers(owner_id),
    )
    assert concepts.status_code == 200
    assert concepts.json()["concepts"][0]["id"] == concept_id

    denied = client.get(
        "/agent/chapters",
        params={"subject_package_id": subject_id},
        headers=_headers(outsider_id),
    )
    assert denied.status_code == 403


def test_attempt_rejects_cross_subject_access(client):
    owner_id, outsider_id, _, _, concept_id = _seed()
    payload = {"concept_id": concept_id, "is_correct": True, "attempt_number": 1}

    denied = client.post("/agent/attempt", json=payload, headers=_headers(outsider_id))
    assert denied.status_code == 403

    accepted = client.post("/agent/attempt", json=payload, headers=_headers(owner_id))
    assert accepted.status_code == 200
    assert accepted.json()["confidence_level"] == 1
