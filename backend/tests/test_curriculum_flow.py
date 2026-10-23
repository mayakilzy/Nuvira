"""CURRICULUM-01 end-to-end fixture and authorization regression tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.models.content import Chapter
from app.models.curriculum import (
    Curriculum, CurriculumUnit, CurriculumVersion, EducationalSystem,
    LearningResource, Lesson, UserLessonProgress,
)
from app.models.subject import Concept, SubjectPackage, UserSubjectAccess
from app.models.user import User
from app.services import curriculum_processing_service
from app.services.remote_import_service import validate_remote_url
from app.workers.tasks import process_curriculum_resource_task
from tests.conftest import TestingSessionLocal, engine


TABLES = [
    UserLessonProgress, Concept, Lesson, Chapter, CurriculumUnit, LearningResource,
    UserSubjectAccess, SubjectPackage, CurriculumVersion, Curriculum,
    EducationalSystem,
]


def _education_schema():
    for model in TABLES:
        model.__table__.drop(engine, checkfirst=True)
    for model in [
        EducationalSystem, Curriculum, CurriculumVersion, SubjectPackage,
        UserSubjectAccess, LearningResource, CurriculumUnit, Chapter, Lesson,
        Concept, UserLessonProgress,
    ]:
        model.__table__.create(engine, checkfirst=True)


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def _users() -> tuple[int, int]:
    db = TestingSessionLocal()
    admin = User(email="curriculum-admin@example.invalid", password_hash=hash_password("password123"), role="admin")
    student = User(email="curriculum-student@example.invalid", password_hash=hash_password("password123"), role="user")
    db.add_all([admin, student]); db.commit(); result = (admin.id, student.id); db.close()
    return result


def _fixture_path() -> Path:
    value = os.getenv("NUVIRA_CURRICULUM_FIXTURE")
    if not value or not Path(value).is_file():
        pytest.skip("NUVIRA_CURRICULUM_FIXTURE is not configured")
    return Path(value)


def test_fixture_import_review_publish_enroll_and_progress(client, tmp_path, monkeypatch):
    _education_schema(); admin_id, student_id = _users()
    monkeypatch.setattr(settings, "CONTENT_STORAGE_ROOT", str(tmp_path / "curriculum"))
    monkeypatch.setattr(settings, "DEV_CURRICULUM_ENROLLMENT_ENABLED", True)
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(process_curriculum_resource_task, "delay", lambda resource_id: None)
    admin = _headers(admin_id); student = _headers(student_id)

    system = client.post("/curricula/admin/systems", headers=admin, json={
        "title": "Syrian secondary education - demo", "country_code": "SY",
    })
    assert system.status_code == 200
    curriculum = client.post("/curricula/admin/curricula", headers=admin, json={
        "educational_system_id": system.json()["id"], "title": "Scientific Baccalaureate demo",
        "academic_level": "Upper secondary", "grade_track": "Scientific",
        "primary_language": "ar", "supported_languages": ["ar"],
        "provenance": "Original Nuvira development fixture",
    })
    version = client.post("/curricula/admin/versions", headers=admin, json={
        "curriculum_id": curriculum.json()["id"], "academic_year": "2026-demo",
        "edition": "1.0", "rights_status": "verified",
    })
    subject = client.post("/curricula/admin/subjects", headers=admin, json={
        "curriculum_version_id": version.json()["id"], "name": "Mathematics",
        "language": "ar", "order_index": 1,
    })
    subject_id = subject.json()["id"]

    fixture = _fixture_path()
    with fixture.open("rb") as handle:
        upload = client.post(
            "/curricula/admin/resources/upload", headers=admin,
            data={
                "subject_package_id": str(subject_id), "title": "Demo mathematics - two lessons",
                "content_language": "ar", "rights_status": "verified",
                "provenance": "Original Nuvira development fixture",
            },
            files={"file": (fixture.name, handle, "application/pdf")},
        )
    assert upload.status_code == 200, upload.text
    resource_id = upload.json()["id"]

    db = TestingSessionLocal()
    curriculum_processing_service.process_resource(db, resource_id)
    db.close()
    reviewed = client.get(f"/curricula/admin/resources/{resource_id}", headers=admin)
    assert reviewed.status_code == 200
    lessons = reviewed.json()["lessons"]
    assert len(lessons) == 2
    extracted = "\n".join(item["content_text"] for item in lessons)
    assert "f′(a) = lim" in extracted
    assert "f′(x) = 9x²" in extracted

    corrected = ["مفهوم المشتقة ومعدل التغير", "قواعد الاشتقاق الأساسية"]
    for lesson, title in zip(lessons, corrected):
        response = client.patch(
            f"/curricula/admin/lessons/{lesson['id']}", headers=admin,
            json={"title": title, "unit_title": "المشتقات والتفاضل", "chapter_title": "المشتقات"},
        )
        assert response.status_code == 200

    unpublished = client.get(f"/curricula/subjects/{subject_id}", headers=student)
    assert unpublished.status_code == 404
    blocked_publish = client.post(f"/curricula/admin/versions/{version.json()['id']}/publish", headers=admin)
    assert blocked_publish.status_code == 409
    approved = client.post(f"/curricula/admin/resources/{resource_id}/approve-review", headers=admin)
    assert approved.status_code == 200
    revised = client.patch(
        f"/curricula/admin/lessons/{lessons[0]['id']}", headers=admin,
        json={"title": corrected[0]},
    )
    assert revised.status_code == 200
    assert client.post(
        f"/curricula/admin/versions/{version.json()['id']}/publish", headers=admin
    ).status_code == 409
    assert client.post(
        f"/curricula/admin/resources/{resource_id}/approve-review", headers=admin
    ).status_code == 200
    published = client.post(f"/curricula/admin/versions/{version.json()['id']}/publish", headers=admin)
    assert published.status_code == 200, published.text
    assert client.patch(
        f"/curricula/admin/lessons/{lessons[0]['id']}", headers=admin,
        json={"title": "Unreviewed live edit"},
    ).status_code == 409

    catalog = client.get("/curricula/catalog", headers=student)
    assert catalog.status_code == 200
    catalog_subject = catalog.json()["curricula"][0]["versions"][0]["subjects"][0]
    assert catalog_subject["id"] == subject_id and not catalog_subject["enrolled"]

    first = client.post(f"/curricula/subjects/{subject_id}/enroll", headers=student)
    second = client.post(f"/curricula/subjects/{subject_id}/enroll", headers=student)
    assert first.json()["created"] is True and second.json()["created"] is False

    structure = client.get(f"/curricula/subjects/{subject_id}", headers=student)
    assert structure.status_code == 200
    published_lessons = structure.json()["resources"][0]["lessons"]
    assert [item["title"] for item in published_lessons] == corrected
    first_lesson = published_lessons[0]
    detail = client.get(f"/curricula/lessons/{first_lesson['id']}", headers=student)
    assert detail.status_code == 200 and "f′(a) = lim" in detail.json()["content_text"]
    assert client.get(f"/curricula/resources/{resource_id}/source", headers=student).content.startswith(b"%PDF-")
    assert client.post(
        f"/curricula/lessons/{first_lesson['id']}/progress", headers=student, json={"completed": True}
    ).status_code == 200
    refreshed = client.get(f"/curricula/subjects/{subject_id}", headers=student)
    assert refreshed.json()["resources"][0]["lessons"][0]["completed"] is True

    fallback = client.post("/agent/chat", headers=student, json={
        "message": "اشرح المشتقة", "subject_package_id": subject_id,
    })
    assert fallback.status_code == 200
    assert fallback.json()["mode"] == "stored-content" and fallback.json()["used_material_context"] is True

    with fixture.open("rb") as handle:
        duplicate = client.post(
            "/curricula/admin/resources/upload", headers=admin,
            data={"subject_package_id": str(subject_id), "title": "Duplicate", "content_language": "ar", "rights_status": "verified"},
            files={"file": (fixture.name, handle, "application/pdf")},
        )
    assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True


def test_curriculum_admin_and_ssrf_controls(client, tmp_path, monkeypatch):
    _education_schema(); admin_id, student_id = _users()
    monkeypatch.setattr(settings, "CONTENT_STORAGE_ROOT", str(tmp_path / "curriculum"))
    student = _headers(student_id)
    denied = client.post("/curricula/admin/systems", headers=student, json={"title": "Denied"})
    assert denied.status_code == 403
    for url in ("http://example.com/book.pdf", "https://127.0.0.1/book.pdf", "https://169.254.169.254/latest/meta-data"):
        with pytest.raises(Exception) as exc:
            validate_remote_url(url)
        assert getattr(exc.value, "status_code", None) == 400

    # A forged extension is rejected before any database resource is created.
    system = EducationalSystem(title="System")
    db = TestingSessionLocal(); db.add(system); db.flush()
    curriculum = Curriculum(educational_system_id=system.id, title="Draft", primary_language="en")
    db.add(curriculum); db.flush()
    version = CurriculumVersion(curriculum_id=curriculum.id, academic_year="2026", edition="1", rights_status="verified")
    db.add(version); db.flush()
    subject = SubjectPackage(curriculum_version_id=version.id, name="Draft subject", language="en", publication_status="draft")
    db.add(subject); db.commit(); subject_id = subject.id; db.close()
    bad = client.post(
        "/curricula/admin/resources/upload", headers=_headers(admin_id),
        data={"subject_package_id": str(subject_id), "title": "Forged", "content_language": "en", "rights_status": "verified"},
        files={"file": ("forged.pdf", b"not a pdf", "application/pdf")},
    )
    assert bad.status_code == 400
    db = TestingSessionLocal(); assert db.query(LearningResource).count() == 0; db.close()
