"""Live PostgreSQL/Celery/HTTP verification for the curriculum publication flow."""
from __future__ import annotations

import io
import os
import time
import uuid

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.models.user import User

API = os.getenv("STAGING_API_URL")
pytestmark = pytest.mark.skipif(not API, reason="STAGING_API_URL is not configured")


def _pdf() -> bytes:
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    for number, title, formula in (
        (1, "Derivative and rate of change", "f'(a) = limit [f(a+h)-f(a)] / h"),
        (2, "Basic differentiation rules", "f'(x) = 9x^2 - 4x + 5"),
    ):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
        })
        stream = DecodedStreamObject()
        content = (
            f"BT /F1 14 Tf 72 740 Td (Unit 01 Lesson {number:02d}) Tj "
            f"0 -28 Td ({title}) Tj 0 -28 Td ({formula}) Tj "
            f"0 -28 Td (Example {number}: reviewed source text) Tj "
            f"0 -28 Td (Exercise {number}: practice problem) Tj ET"
        )
        stream.set_data(content.encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO(); writer.write(output); return output.getvalue()


def _seed_users() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    suffix = uuid.uuid4().hex
    db = SessionLocal()
    users = [
        User(email=f"curriculum-admin-{suffix}@example.invalid", password_hash=hash_password("SyntheticPass1234"), role="admin"),
        User(email=f"curriculum-student-a-{suffix}@example.invalid", password_hash=hash_password("SyntheticPass1234"), role="user"),
        User(email=f"curriculum-student-b-{suffix}@example.invalid", password_hash=hash_password("SyntheticPass1234"), role="user"),
    ]
    db.add_all(users); db.commit(); ids = [user.id for user in users]; db.close()
    return tuple({"Authorization": f"Bearer {create_access_token(str(user_id))}"} for user_id in ids)


def test_live_curriculum_import_publish_and_isolation():
    admin, student_a, student_b = _seed_users()
    with httpx.Client(base_url=API, timeout=30) as client:
        system = client.post("/curricula/admin/systems", headers=admin, json={"title": "Synthetic staging system", "country_code": "ZZ"})
        assert system.status_code == 200, system.text
        curriculum = client.post("/curricula/admin/curricula", headers=admin, json={
            "educational_system_id": system.json()["id"], "title": "Synthetic staging curriculum",
            "primary_language": "en", "supported_languages": ["en"],
        })
        version = client.post("/curricula/admin/versions", headers=admin, json={
            "curriculum_id": curriculum.json()["id"], "academic_year": "staging-2026",
            "edition": uuid.uuid4().hex[:8], "rights_status": "verified",
        })
        subject = client.post("/curricula/admin/subjects", headers=admin, json={
            "curriculum_version_id": version.json()["id"], "name": "Synthetic mathematics", "language": "en",
        })
        subject_id = subject.json()["id"]
        denied_admin = client.post("/curricula/admin/systems", headers=student_a, json={"title": "Denied"})
        assert denied_admin.status_code == 403
        hidden = client.get(f"/curricula/subjects/{subject_id}", headers=student_a)
        assert hidden.status_code == 404

        source = _pdf()
        upload = client.post(
            "/curricula/admin/resources/upload", headers=admin,
            data={"subject_package_id": subject_id, "title": "Synthetic two-lesson book", "content_language": "en", "rights_status": "verified"},
            files={"file": ("synthetic-two-lessons.pdf", source, "application/pdf")},
        )
        assert upload.status_code == 200, upload.text
        resource_id = upload.json()["id"]
        status = upload.json()
        for _ in range(60):
            status = client.get(f"/curricula/admin/resources/{resource_id}", headers=admin).json()
            if status["processing_status"] in {"review", "failed"}:
                break
            time.sleep(1)
        assert status["processing_status"] == "review", status
        assert len(status["lessons"]) == 2
        assert "9x^2 - 4x + 5" in "\n".join(item["content_text"] for item in status["lessons"])
        assert client.post(f"/curricula/admin/versions/{version.json()['id']}/publish", headers=admin).status_code == 409
        approved = client.post(f"/curricula/admin/resources/{resource_id}/approve-review", headers=admin)
        assert approved.status_code == 200, approved.text

        duplicate = client.post(
            "/curricula/admin/resources/upload", headers=admin,
            data={"subject_package_id": subject_id, "title": "Duplicate", "content_language": "en", "rights_status": "verified"},
            files={"file": ("duplicate.pdf", source, "application/pdf")},
        )
        assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True
        assert client.post(f"/curricula/admin/versions/{version.json()['id']}/publish", headers=student_a).status_code == 403
        published = client.post(f"/curricula/admin/versions/{version.json()['id']}/publish", headers=admin)
        assert published.status_code == 200, published.text

        enrollment = client.post(f"/curricula/subjects/{subject_id}/enroll", headers=student_a)
        repeated = client.post(f"/curricula/subjects/{subject_id}/enroll", headers=student_a)
        assert enrollment.status_code == 200 and enrollment.json()["created"] is True
        assert repeated.status_code == 200 and repeated.json()["created"] is False
        assert client.get(f"/curricula/subjects/{subject_id}", headers=student_b).status_code == 403
        structure = client.get(f"/curricula/subjects/{subject_id}", headers=student_a).json()
        lesson_id = structure["resources"][0]["lessons"][0]["id"]
        assert client.get(f"/curricula/lessons/{lesson_id}", headers=student_a).status_code == 200
        assert client.get(f"/curricula/lessons/{lesson_id}", headers=student_b).status_code == 403
        assert client.get(f"/curricula/resources/{resource_id}/source", headers=student_a).content.startswith(b"%PDF-")
        assert client.post(f"/curricula/lessons/{lesson_id}/progress", headers=student_a, json={"completed": True}).status_code == 200
