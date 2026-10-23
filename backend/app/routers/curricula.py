"""Administrator curriculum intake and authenticated student catalog APIs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.content import Chapter
from app.models.curriculum import (
    Curriculum,
    CurriculumUnit,
    CurriculumVersion,
    EducationalSystem,
    LearningResource,
    Lesson,
    UserLessonProgress,
)
from app.models.subject import Concept, SubjectPackage, UserSubjectAccess
from app.models.user import User
from app.services.content_storage import get_content_storage, safe_filename, validate_pdf_signature
from app.services.remote_import_service import fetch_pdf

router = APIRouter(prefix="/curricula", tags=["curricula"])

RightsState = Literal["verified", "pending", "restricted", "rejected"]


class SystemIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    system_type: str | None = Field(default=None, max_length=80)
    description: str | None = None


class CurriculumIn(BaseModel):
    educational_system_id: int
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    academic_level: str | None = Field(default=None, max_length=120)
    grade_track: str | None = Field(default=None, max_length=160)
    primary_language: str = Field(default="en", min_length=2, max_length=35)
    supported_languages: list[str] = Field(default_factory=list)
    provenance: str | None = None


class VersionIn(BaseModel):
    curriculum_id: int
    academic_year: str = Field(min_length=2, max_length=40)
    edition: str = Field(default="1", max_length=80)
    title: str | None = Field(default=None, max_length=255)
    rights_status: RightsState = "pending"


class SubjectIn(BaseModel):
    curriculum_version_id: int
    name: str = Field(min_length=2, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    language: str = Field(default="en", min_length=2, max_length=35)
    order_index: int = Field(default=0, ge=0)


class RemoteResourceIn(BaseModel):
    subject_package_id: int
    title: str = Field(min_length=2, max_length=255)
    url: str = Field(min_length=8, max_length=2048)
    content_language: str = Field(default="en", min_length=2, max_length=35)
    resource_type: str = Field(default="textbook", max_length=40)
    rights_status: RightsState = "pending"
    provenance: str | None = None


class LessonPatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    content_text: str | None = None
    unit_title: str | None = Field(default=None, min_length=2, max_length=255)
    chapter_title: str | None = Field(default=None, min_length=2, max_length=255)
    examples: list[str] | None = None
    exercises: list[str] | None = None


class ProgressIn(BaseModel):
    completed: bool = False


def _require_subject(db: Session, subject_id: int) -> SubjectPackage:
    subject = db.query(SubjectPackage).filter(SubjectPackage.id == subject_id).first()
    if not subject:
        raise HTTPException(404, "Subject not found")
    return subject


def _require_enrolled_subject(db: Session, user: User, subject_id: int) -> SubjectPackage:
    subject = _require_subject(db, subject_id)
    if user.role != "admin":
        if subject.publication_status != "published":
            raise HTTPException(404, "Published subject not found")
        enrollment = db.query(UserSubjectAccess).filter(
            UserSubjectAccess.user_id == user.id,
            UserSubjectAccess.subject_package_id == subject.id,
            UserSubjectAccess.is_active.is_(True),
        ).first()
        if not enrollment:
            raise HTTPException(403, "Enrollment required")
    return subject


def _queue_resource(db: Session, resource: LearningResource) -> None:
    try:
        from app.workers.tasks import process_curriculum_resource_task
        process_curriculum_resource_task.delay(resource.id)
    except Exception:
        resource.processing_status = "failed"
        resource.error_code = "QUEUE_UNAVAILABLE"
        resource.error_note = "Processing could not be queued. Retry when the worker is available."
        db.commit()
        raise HTTPException(503, "Curriculum source was stored but processing could not be queued")


def _cleanup_unreferenced_storage(db: Session, storage_key: str | None) -> None:
    if storage_key and not db.query(LearningResource).filter(LearningResource.storage_key == storage_key).first():
        get_content_storage().remove(storage_key)


def _resource_payload(db: Session, resource: LearningResource) -> dict:
    lessons = db.query(Lesson).filter(Lesson.learning_resource_id == resource.id).order_by(Lesson.order_index).all()
    return {
        "id": resource.id,
        "subject_package_id": resource.subject_package_id,
        "title": resource.title,
        "content_language": resource.content_language,
        "publication_status": resource.publication_status,
        "rights_status": resource.rights_status,
        "processing_status": resource.processing_status,
        "processing_job_id": resource.processing_job_id,
        "source_type": resource.source_type,
        "source_url": resource.source_url,
        "original_filename": resource.original_filename,
        "mime_type": resource.mime_type,
        "file_size": resource.file_size,
        "sha256": resource.sha256,
        "error_code": resource.error_code,
        "error_note": resource.error_note,
        "reviewed_at": resource.reviewed_at,
        "lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "order_index": lesson.order_index,
                "page_start": lesson.page_start,
                "page_end": lesson.page_end,
                "content_language": lesson.content_language,
                "publication_status": lesson.publication_status,
                "examples": lesson.examples_json or [],
                "exercises": lesson.exercises_json or [],
                "content_text": lesson.content_text,
                "unit_id": lesson.unit_id,
                "chapter_id": lesson.chapter_id,
            }
            for lesson in lessons
        ],
    }


def _create_resource(
    db: Session,
    *,
    subject: SubjectPackage,
    admin: User,
    title: str,
    content_language: str,
    resource_type: str,
    rights_status: str,
    provenance: str | None,
    source_type: str,
    source_url: str | None,
    original_filename: str,
    mime_type: str,
    file_size: int,
    checksum: str,
    storage_key: str,
) -> tuple[LearningResource, bool]:
    duplicate = db.query(LearningResource).filter(
        LearningResource.subject_package_id == subject.id,
        LearningResource.sha256 == checksum,
    ).first()
    if duplicate:
        return duplicate, True
    used = db.query(func.coalesce(func.sum(LearningResource.file_size), 0)).scalar() or 0
    if used + file_size > settings.CONTENT_STORAGE_QUOTA_BYTES:
        raise HTTPException(413, "Curriculum storage quota exceeded")
    resource = LearningResource(
        subject_package_id=subject.id,
        title=title,
        content_language=content_language,
        resource_type=resource_type,
        rights_status=rights_status,
        provenance=provenance,
        source_type=source_type,
        source_url=source_url,
        storage_key=storage_key,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
        sha256=checksum,
        processing_job_id=str(uuid.uuid4()),
        processing_status="queued",
        publication_status="processing",
        uploaded_by_user_id=admin.id,
    )
    subject.publication_status = "draft"
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource, False


@router.post("/admin/systems")
def create_system(data: SystemIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    system = EducationalSystem(**data.model_dump())
    db.add(system); db.commit(); db.refresh(system)
    return {"id": system.id, "title": system.title}


@router.post("/admin/curricula")
def create_curriculum(data: CurriculumIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.query(EducationalSystem).filter(EducationalSystem.id == data.educational_system_id).first():
        raise HTTPException(404, "Educational system not found")
    item = Curriculum(**data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "title": item.title, "publication_status": item.publication_status}


@router.post("/admin/versions")
def create_version(data: VersionIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.query(Curriculum).filter(Curriculum.id == data.curriculum_id).first():
        raise HTTPException(404, "Curriculum not found")
    item = CurriculumVersion(**data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "publication_status": item.publication_status}


@router.post("/admin/subjects")
def create_subject(data: SubjectIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.query(CurriculumVersion).filter(CurriculumVersion.id == data.curriculum_version_id).first():
        raise HTTPException(404, "Curriculum version not found")
    item = SubjectPackage(**data.model_dump(), review_status="unreviewed", publication_status="draft")
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "name": item.name, "publication_status": item.publication_status}


@router.post("/admin/resources/upload")
async def upload_resource(
    subject_package_id: int = Form(...),
    title: str = Form(...),
    content_language: str = Form("en"),
    resource_type: str = Form("textbook"),
    rights_status: RightsState = Form("pending"),
    provenance: str | None = Form(None),
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    subject = _require_subject(db, subject_package_id)
    storage = get_content_storage()
    temp, size, checksum = await storage.receive_upload(file)
    stored = None
    try:
        mime = validate_pdf_signature(temp, file.content_type)
        duplicate = db.query(LearningResource).filter(
            LearningResource.subject_package_id == subject.id,
            LearningResource.sha256 == checksum,
        ).first()
        if duplicate:
            temp.unlink(missing_ok=True)
            return {**_resource_payload(db, duplicate), "duplicate": True}
        stored = storage.finalize(temp, checksum, safe_filename(file.filename), mime)
        resource, _ = _create_resource(
            db, subject=subject, admin=admin, title=title, content_language=content_language,
            resource_type=resource_type, rights_status=rights_status, provenance=provenance,
            source_type="upload", source_url=None, original_filename=stored.original_filename,
            mime_type=stored.mime_type, file_size=size, checksum=checksum, storage_key=stored.storage_key,
        )
        _queue_resource(db, resource)
        return {**_resource_payload(db, resource), "duplicate": False}
    except Exception:
        temp.unlink(missing_ok=True)
        _cleanup_unreferenced_storage(db, stored.storage_key if stored else None)
        raise


@router.post("/admin/resources/import-url")
async def import_remote_resource(
    data: RemoteResourceIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    subject = _require_subject(db, data.subject_package_id)
    storage = get_content_storage()
    temp, size, checksum, final_url, filename = await fetch_pdf(data.url, storage)
    stored = None
    try:
        mime = validate_pdf_signature(temp, "application/pdf")
        duplicate = db.query(LearningResource).filter(
            LearningResource.subject_package_id == subject.id,
            LearningResource.sha256 == checksum,
        ).first()
        if duplicate:
            temp.unlink(missing_ok=True)
            return {**_resource_payload(db, duplicate), "duplicate": True}
        stored = storage.finalize(temp, checksum, filename, mime)
        resource, _ = _create_resource(
            db, subject=subject, admin=admin, title=data.title,
            content_language=data.content_language, resource_type=data.resource_type,
            rights_status=data.rights_status, provenance=data.provenance, source_type="remote",
            source_url=final_url, original_filename=stored.original_filename, mime_type=stored.mime_type,
            file_size=size, checksum=checksum, storage_key=stored.storage_key,
        )
        _queue_resource(db, resource)
        return {**_resource_payload(db, resource), "duplicate": False}
    except Exception:
        temp.unlink(missing_ok=True)
        _cleanup_unreferenced_storage(db, stored.storage_key if stored else None)
        raise


@router.post("/admin/resources/{resource_id}/retry")
def retry_resource(resource_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        raise HTTPException(404, "Resource not found")
    if resource.publication_status == "published":
        raise HTTPException(409, "Unpublish the curriculum version before reprocessing a published resource")
    if resource.processing_status not in {"failed", "review"}:
        raise HTTPException(409, "Resource is already queued or processing")
    resource.processing_status = "queued"
    resource.error_code = None
    resource.error_note = None
    db.commit()
    _queue_resource(db, resource)
    return _resource_payload(db, resource)


@router.get("/admin/resources/{resource_id}")
def get_admin_resource(resource_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        raise HTTPException(404, "Resource not found")
    return _resource_payload(db, resource)


@router.patch("/admin/lessons/{lesson_id}")
def update_lesson(data: LessonPatch, lesson_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    resource = db.query(LearningResource).filter(LearningResource.id == lesson.learning_resource_id).one()
    if resource.publication_status in {"published", "retired"}:
        raise HTTPException(409, "Unpublish the curriculum version before editing published content")
    values = data.model_dump(exclude_unset=True)
    for field in ("title", "description", "content_text"):
        if field in values:
            setattr(lesson, field, values[field])
    if "examples" in values:
        lesson.examples_json = values["examples"]
    if "exercises" in values:
        lesson.exercises_json = values["exercises"]
    if values.get("unit_title") and lesson.unit_id:
        db.query(CurriculumUnit).filter(CurriculumUnit.id == lesson.unit_id).update({"title": values["unit_title"]})
    if values.get("chapter_title") and lesson.chapter_id:
        db.query(Chapter).filter(Chapter.id == lesson.chapter_id).update({"title": values["chapter_title"]})
    if values.get("title"):
        db.query(Concept).filter(Concept.lesson_id == lesson.id).update({"name": values["title"]})
    resource.reviewed_at = None
    db.commit(); db.refresh(lesson)
    return {"id": lesson.id, "title": lesson.title, "publication_status": lesson.publication_status}


@router.post("/admin/resources/{resource_id}/approve-review")
def approve_resource_review(resource_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        raise HTTPException(404, "Resource not found")
    if resource.processing_status != "review":
        raise HTTPException(409, "Resource extraction must complete before review approval")
    if not db.query(Lesson).filter(Lesson.learning_resource_id == resource.id).count():
        raise HTTPException(409, "At least one reviewed lesson is required")
    resource.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": resource.id, "reviewed": True, "reviewed_at": resource.reviewed_at}


@router.post("/admin/versions/{version_id}/publish")
def publish_version(version_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    version = db.query(CurriculumVersion).filter(CurriculumVersion.id == version_id).first()
    if not version:
        raise HTTPException(404, "Curriculum version not found")
    if version.publication_status == "retired":
        raise HTTPException(409, "Retired curriculum versions cannot be republished")
    if version.rights_status != "verified":
        raise HTTPException(409, "Curriculum version rights must be verified before publication")
    subjects = db.query(SubjectPackage).filter(SubjectPackage.curriculum_version_id == version.id).all()
    if not subjects:
        raise HTTPException(409, "At least one subject is required")
    subject_ids = [subject.id for subject in subjects]
    resources = db.query(LearningResource).filter(LearningResource.subject_package_id.in_(subject_ids)).all()
    if not resources:
        raise HTTPException(409, "At least one reviewed resource is required")
    if any(
        resource.processing_status != "review"
        or resource.rights_status != "verified"
        or resource.reviewed_at is None
        for resource in resources
    ):
        raise HTTPException(409, "Every resource must be explicitly reviewed and rights-verified")
    lessons = db.query(Lesson).filter(Lesson.subject_package_id.in_(subject_ids)).all()
    if not lessons:
        raise HTTPException(409, "At least one reviewed lesson is required")
    now = datetime.now(timezone.utc)
    version.publication_status = "published"; version.published_at = now
    curriculum = db.query(Curriculum).filter(Curriculum.id == version.curriculum_id).one()
    curriculum.publication_status = "published"
    for subject in subjects:
        subject.publication_status = "published"; subject.review_status = "self_reviewed"
    for resource in resources:
        resource.publication_status = "published"; resource.reviewed_at = now; resource.published_at = now
    for lesson in lessons:
        lesson.publication_status = "published"
    db.commit()
    return {"id": version.id, "publication_status": "published"}


@router.post("/admin/versions/{version_id}/unpublish")
def unpublish_version(version_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    version = db.query(CurriculumVersion).filter(CurriculumVersion.id == version_id).first()
    if not version:
        raise HTTPException(404, "Curriculum version not found")
    if version.publication_status == "retired":
        raise HTTPException(409, "Retired curriculum versions cannot be unpublished")
    version.publication_status = "review"
    subjects = db.query(SubjectPackage).filter(SubjectPackage.curriculum_version_id == version.id).all()
    subject_ids = [subject.id for subject in subjects]
    for subject in subjects:
        subject.publication_status = "review"
    db.query(LearningResource).filter(LearningResource.subject_package_id.in_(subject_ids)).update(
        {"publication_status": "review"}, synchronize_session=False
    )
    db.query(Lesson).filter(Lesson.subject_package_id.in_(subject_ids)).update(
        {"publication_status": "review"}, synchronize_session=False
    )
    db.commit()
    return {"id": version.id, "publication_status": "review"}


@router.post("/admin/versions/{version_id}/retire")
def retire_version(version_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    version = db.query(CurriculumVersion).filter(CurriculumVersion.id == version_id).first()
    if not version:
        raise HTTPException(404, "Curriculum version not found")
    version.publication_status = "retired"
    subjects = db.query(SubjectPackage).filter(SubjectPackage.curriculum_version_id == version.id).all()
    subject_ids = [subject.id for subject in subjects]
    for subject in subjects:
        subject.publication_status = "retired"
    db.query(LearningResource).filter(LearningResource.subject_package_id.in_(subject_ids)).update(
        {"publication_status": "retired"}, synchronize_session=False
    )
    db.query(Lesson).filter(Lesson.subject_package_id.in_(subject_ids)).update(
        {"publication_status": "retired"}, synchronize_session=False
    )
    db.commit()
    return {"id": version.id, "publication_status": "retired", "history_preserved": True}


@router.get("/admin/library")
def admin_library(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    curricula = db.query(Curriculum).order_by(Curriculum.created_at.desc()).all()
    return {
        "curricula": [
            {
                "id": curriculum.id, "title": curriculum.title,
                "publication_status": curriculum.publication_status,
                "versions": [
                    {
                        "id": version.id, "academic_year": version.academic_year,
                        "edition": version.edition, "rights_status": version.rights_status,
                        "publication_status": version.publication_status,
                        "subjects": [
                            {
                                "id": subject.id, "name": subject.name, "language": subject.language,
                                "publication_status": subject.publication_status,
                                "resources": [
                                    {"id": resource.id, "title": resource.title,
                                     "processing_status": resource.processing_status,
                                     "publication_status": resource.publication_status}
                                    for resource in db.query(LearningResource).filter(
                                        LearningResource.subject_package_id == subject.id
                                    ).order_by(LearningResource.created_at.desc())
                                ],
                            }
                            for subject in db.query(SubjectPackage).filter(
                                SubjectPackage.curriculum_version_id == version.id
                            ).order_by(SubjectPackage.order_index, SubjectPackage.name)
                        ],
                    }
                    for version in db.query(CurriculumVersion).filter(
                        CurriculumVersion.curriculum_id == curriculum.id
                    ).order_by(CurriculumVersion.created_at.desc())
                ],
            }
            for curriculum in curricula
        ]
    }


@router.get("/catalog")
def catalog(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    curricula = db.query(Curriculum).filter(Curriculum.publication_status == "published").order_by(Curriculum.title).all()
    enrolled = {
        row.subject_package_id for row in db.query(UserSubjectAccess).filter(
            UserSubjectAccess.user_id == user.id, UserSubjectAccess.is_active.is_(True)
        )
    }
    payload = []
    for curriculum in curricula:
        versions = db.query(CurriculumVersion).filter(
            CurriculumVersion.curriculum_id == curriculum.id,
            CurriculumVersion.publication_status == "published",
        ).order_by(CurriculumVersion.academic_year.desc(), CurriculumVersion.edition.desc()).all()
        payload.append({
            "id": curriculum.id, "title": curriculum.title, "description": curriculum.description,
            "academic_level": curriculum.academic_level, "grade_track": curriculum.grade_track,
            "primary_language": curriculum.primary_language,
            "versions": [
                {
                    "id": version.id, "academic_year": version.academic_year, "edition": version.edition,
                    "subjects": [
                        {
                            "id": subject.id, "name": subject.name, "description": subject.description,
                            "language": subject.language, "enrolled": subject.id in enrolled,
                        }
                        for subject in db.query(SubjectPackage).filter(
                            SubjectPackage.curriculum_version_id == version.id,
                            SubjectPackage.publication_status == "published",
                        ).order_by(SubjectPackage.order_index, SubjectPackage.name)
                    ],
                }
                for version in versions
            ],
        })
    return {"curricula": payload, "development_enrollment_enabled": settings.DEV_CURRICULUM_ENROLLMENT_ENABLED and settings.ENV != "production"}


@router.post("/subjects/{subject_id}/enroll")
def enroll(subject_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not settings.DEV_CURRICULUM_ENROLLMENT_ENABLED or settings.ENV == "production":
        raise HTTPException(403, "Development enrollment is disabled")
    subject = _require_subject(db, subject_id)
    if subject.publication_status != "published":
        raise HTTPException(404, "Published subject not found")
    existing = db.query(UserSubjectAccess).filter(
        UserSubjectAccess.user_id == user.id,
        UserSubjectAccess.subject_package_id == subject.id,
    ).first()
    if existing:
        existing.is_active = True
        db.commit()
        return {"subject_id": subject.id, "enrolled": True, "created": False}
    db.add(UserSubjectAccess(user_id=user.id, subject_package_id=subject.id, source="development", is_active=True))
    db.commit()
    return {"subject_id": subject.id, "enrolled": True, "created": True}


@router.get("/subjects/{subject_id}")
def subject_structure(subject_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subject = _require_enrolled_subject(db, user, subject_id)
    resources = db.query(LearningResource).filter(
        LearningResource.subject_package_id == subject.id,
        LearningResource.publication_status == "published",
    ).order_by(LearningResource.order_index, LearningResource.title).all()
    progress = {
        row.lesson_id: row for row in db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user.id)
    }
    return {
        "id": subject.id, "name": subject.name, "language": subject.language,
        "resources": [
            {
                "id": resource.id, "title": resource.title, "content_language": resource.content_language,
                "lessons": [
                    {
                        "id": lesson.id, "title": lesson.title, "description": lesson.description,
                        "order_index": lesson.order_index, "page_start": lesson.page_start,
                        "page_end": lesson.page_end, "content_language": lesson.content_language,
                        "completed": bool(progress.get(lesson.id) and progress[lesson.id].completed),
                    }
                    for lesson in db.query(Lesson).filter(
                        Lesson.learning_resource_id == resource.id,
                        Lesson.publication_status == "published",
                    ).order_by(Lesson.order_index)
                ],
            }
            for resource in resources
        ],
    }


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or lesson.publication_status != "published":
        raise HTTPException(404, "Published lesson not found")
    _require_enrolled_subject(db, user, lesson.subject_package_id)
    return {
        "id": lesson.id, "title": lesson.title, "description": lesson.description,
        "content_text": lesson.content_text, "content_language": lesson.content_language,
        "page_start": lesson.page_start, "page_end": lesson.page_end,
        "examples": lesson.examples_json or [], "exercises": lesson.exercises_json or [],
        "resource_id": lesson.learning_resource_id,
    }


@router.post("/lessons/{lesson_id}/progress")
def save_progress(data: ProgressIn, lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or lesson.publication_status != "published":
        raise HTTPException(404, "Published lesson not found")
    _require_enrolled_subject(db, user, lesson.subject_package_id)
    item = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == user.id, UserLessonProgress.lesson_id == lesson.id
    ).first()
    now = datetime.now(timezone.utc)
    if not item:
        item = UserLessonProgress(user_id=user.id, lesson_id=lesson.id)
        db.add(item)
    item.completed = data.completed
    item.last_opened_at = now
    item.completed_at = now if data.completed else None
    db.commit()
    return {"lesson_id": lesson.id, "completed": item.completed}


@router.get("/resources/{resource_id}/source")
def source_file(resource_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource or resource.publication_status != "published":
        raise HTTPException(404, "Published resource not found")
    _require_enrolled_subject(db, user, resource.subject_package_id)
    try:
        path = get_content_storage().path_for(resource.storage_key)
    except FileNotFoundError:
        raise HTTPException(404, "Source file is unavailable")
    return FileResponse(path, media_type=resource.mime_type, filename=resource.original_filename)
