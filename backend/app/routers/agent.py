"""
=============================================================================
 AGENT ROUTER — Generic Study Companion (subject-agnostic)
=============================================================================
"""
import os
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.subject import Concept, SubjectPackage, UserSubjectAccess
from app.models.content import Chapter, UploadedDocument
from app.models.preferences import UserPreferences
from app.models.study import StudyLog
from app.services import ai_service, companion_service, embedding_service, vector_service

router = APIRouter(prefix="/agent", tags=["agent"])

UPLOAD_DIR = "/app/uploads"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

LANGUAGE_NAMES = {"de": "Deutsch", "en": "English", "ar": "Arabisch"}


def build_system_prompt(
    user_name: str,
    subject_name: str,
    university: str | None,
    teaching_language: str,
    retrieved_context: str | None = None,
) -> str:
    """
    موجّه نظام معمم — يعمل لأي مادة/جامعة، بلغة تدريس المادة نفسها
    (subject_packages.language)، لا لغة ثابتة ولا لغة واجهة المستخدم.
    """
    lang_name = LANGUAGE_NAMES.get(teaching_language, "Deutsch")
    context_line = f" ({university})" if university else ""

    base = f"""You are {user_name}'s friendly study companion for the course \
"{subject_name}"{context_line}.

LANGUAGE:
- Respond EXCLUSIVELY in {lang_name}. Match the exact terminology used in \
the official course material whenever it is available below.
- Address them informally/warmly, appropriate to {lang_name}'s conventions \
(e.g. "du" in German, first name in English).

NAME AND TONE:
- Use the name "{user_name}" naturally, not in every sentence.
- Warm, calm, never rushed. Not overly enthusiastic.

TOPIC BOUNDARIES:
- Help ONLY with topics from "{subject_name}". Politely decline other topics.

HANDLING MISTAKES:
- NEVER say the words "wrong", "error", "incorrect", or "grade" (or their \
equivalents in {lang_name}).
- 1st wrong attempt: ask a guiding question, no hint.
- 2nd attempt: gentle hint pointing to the part to re-check.
- 3rd attempt: explain the answer calmly and completely, note how close they were.

EXPLANATION STYLE:
- Start new concepts with an everyday-life analogy before the formal term.
"""

    if retrieved_context:
        base += f"""

OFFICIAL MATERIAL (excerpt from the actual course material — takes priority \
over your general knowledge when relevant):
---
{retrieved_context}
---
Base your answer primarily on this excerpt when it fits the question. Do not \
mention that you received an "excerpt" or "context" — speak as if you already \
know this material. If it's not relevant, use your general knowledge.
"""
    return base


def _subject_context(db: Session, subject_package_id: int) -> SubjectPackage | None:
    return db.query(SubjectPackage).filter(SubjectPackage.id == subject_package_id).first()


def _require_subject_access(db: Session, user: User, subject_package_id: int) -> SubjectPackage:
    subject = _subject_context(db, subject_package_id)
    if not subject:
        raise HTTPException(404, "Subject not found")
    if user.role != "admin":
        grant = (
            db.query(UserSubjectAccess)
            .filter(
                UserSubjectAccess.user_id == user.id,
                UserSubjectAccess.subject_package_id == subject_package_id,
            )
            .first()
        )
        if not grant:
            raise HTTPException(403, "You do not have access to this subject")
    return subject


def _require_concept_access(db: Session, user: User, concept_id: int) -> Concept:
    concept = db.query(Concept).filter(Concept.id == concept_id).first()
    if not concept:
        raise HTTPException(404, "Concept not found")
    _require_subject_access(db, user, concept.subject_package_id)
    return concept


@router.get("/subjects")
def list_subjects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SubjectPackage)
    if user.role != "admin":
        query = query.join(
            UserSubjectAccess,
            UserSubjectAccess.subject_package_id == SubjectPackage.id,
        ).filter(UserSubjectAccess.user_id == user.id)
    subjects = query.order_by(SubjectPackage.name).all()
    return {
        "subjects": [
            {
                "id": subject.id,
                "name": subject.name,
                "university": subject.university,
                "language": subject.language,
                "review_status": subject.review_status,
            }
            for subject in subjects
        ]
    }


# ── محادثة المساعد ────────────────────────────────────────────
class ChatIn(BaseModel):
    message: str
    subject_package_id: int | None = None
    chapter_id: int | None = None


@router.post("/chat")
async def chat(data: ChatIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    name = user.full_name or "there"

    subject_name, university, teaching_language = "General Studies", None, "de"
    if data.subject_package_id:
        subject = _require_subject_access(db, user, data.subject_package_id)
        subject_name = subject.name
        university = subject.university
        teaching_language = subject.language

    if data.chapter_id:
        chapter = db.query(Chapter).filter(Chapter.id == data.chapter_id).first()
        if not chapter or chapter.subject_package_id != data.subject_package_id:
            raise HTTPException(400, "Chapter does not belong to the selected subject")

    retrieved_context = None
    if data.subject_package_id:
        try:
            query_vector = await embedding_service.get_embedding(data.message)
            results = vector_service.search_scoped(
                db, query_vector,
                subject_package_id=data.subject_package_id,
                chapter_id=data.chapter_id,
                k=4,
            )
            if results:
                retrieved_context = "\n---\n".join(r["content"] for r in results)
        except embedding_service.EmbeddingServiceError:
            retrieved_context = None

    reply = await ai_service.chat(
        messages=[
            {
                "role": "system",
                "content": build_system_prompt(
                    name, subject_name, university, teaching_language, retrieved_context
                ),
            },
            {"role": "user", "content": data.message},
        ]
    )
    return {"reply": reply, "used_material_context": retrieved_context is not None}


# ── تفضيلات المستخدم — لغة الواجهة والمظهر (منفصلة عن لغة التدريس) ──
class PreferencesIn(BaseModel):
    ui_language: Literal["de", "en", "ar"] | None = None
    theme: Literal["light", "dark", "system"] | None = None
    avatar_corner_enabled: bool | None = None


@router.get("/preferences")
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return {
        "ui_language": prefs.ui_language,
        "theme": prefs.theme,
        "avatar_corner_enabled": prefs.avatar_corner_enabled,
    }


@router.put("/preferences")
def update_preferences(data: PreferencesIn, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)

    if data.ui_language is not None:
        prefs.ui_language = data.ui_language
    if data.theme is not None:
        prefs.theme = data.theme
    if data.avatar_corner_enabled is not None:
        prefs.avatar_corner_enabled = data.avatar_corner_enabled

    db.commit()
    db.refresh(prefs)
    return {
        "ui_language": prefs.ui_language,
        "theme": prefs.theme,
        "avatar_corner_enabled": prefs.avatar_corner_enabled,
    }


# ── الأفاتار ───────────────────────────────────────────────────
@router.post("/session/start")
def session_start(session_key: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    avatar = companion_service.get_or_rotate_avatar(db, user.id, session_key)
    return {"avatar": avatar}


# ── الثقة / التكرار المتباعد / معايرة النغمة ───────────────────
class AttemptIn(BaseModel):
    concept_id: int
    is_correct: bool
    attempt_number: int
    session_note: str | None = None


@router.post("/attempt")
def attempt(data: AttemptIn, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    _require_concept_access(db, user, data.concept_id)
    if data.attempt_number not in (1, 2, 3):
        raise HTTPException(400, "attempt_number must be 1, 2, or 3")
    name = user.full_name or "there"
    result = companion_service.record_attempt(
        db, user.id, data.concept_id, data.is_correct, data.attempt_number, data.session_note
    )
    streak = result["streak"]

    triggered_phrase = None
    if streak["type"] == "incorrect" and streak["count"] >= 3:
        triggered_phrase = companion_service.pick_phrase(db, user.id, "break_invite", name=name)
    elif streak["type"] == "correct" and streak["count"] >= 3:
        triggered_phrase = companion_service.pick_phrase(db, user.id, "encouragement", name=name)

    return {
        "confidence_level": result["confidence_level"],
        "streak": streak,
        "companion_message": triggered_phrase,
    }


@router.get("/fun-fact")
def fun_fact(concept_id: int, minute: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    _require_concept_access(db, user, concept_id)
    name = user.full_name or "there"
    fact = companion_service.pick_fun_fact(db, user.id, concept_id)
    if not fact:
        return {"fact": None}
    companion_service.mark_fun_fact_shown(db, user.id, fact["id"], minute)
    intro = companion_service.pick_phrase(db, user.id, "fun_fact_intro", name=name)
    return {"fact": {"intro": intro, "text": fact["text"]}}


@router.get("/review-queue")
def review_queue(subject_package_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _require_subject_access(db, user, subject_package_id)
    due = companion_service.concepts_due_for_review(db, user.id, subject_package_id)
    return {"due_concepts": [{"id": c.id, "name": c.name} for c in due]}


# ── الفصول ─────────────────────────────────────────────────────
@router.get("/chapters")
def list_chapters(subject_package_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _require_subject_access(db, user, subject_package_id)
    chapters = (
        db.query(Chapter)
        .filter(Chapter.subject_package_id == subject_package_id)
        .order_by(Chapter.chapter_number)
        .all()
    )
    return {"chapters": [{"id": c.id, "number": c.chapter_number, "title": c.title} for c in chapters]}


@router.get("/concepts")
def list_concepts(
    subject_package_id: int,
    chapter_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_subject_access(db, user, subject_package_id)
    if chapter_id is not None:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter or chapter.subject_package_id != subject_package_id:
            raise HTTPException(404, "Chapter not found in this subject")

    # Concepts predate chapter associations in the current schema. Return the
    # authorized subject's concepts and expose this limitation explicitly.
    concepts = (
        db.query(Concept)
        .filter(Concept.subject_package_id == subject_package_id)
        .order_by(Concept.name)
        .all()
    )
    return {
        "chapter_filter_applied": False,
        "concepts": [
            {
                "id": concept.id,
                "name": concept.name,
                "everyday_analogy": concept.everyday_analogy,
                "mechanism": concept.mechanism_json,
                "difficulty": concept.difficulty,
                "official_source_note": concept.official_source_note,
            }
            for concept in concepts
        ],
    }


# ── رفع ومتابعة الملفات ─────────────────────────────────────────
@router.post("/materials/upload")
async def upload_material(
    subject_package_id: int = Form(...),
    chapter_id: int | None = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_subject_access(db, user, subject_package_id)
    if chapter_id is not None:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter or chapter.subject_package_id != subject_package_id:
            raise HTTPException(400, "Chapter does not belong to the selected subject")
    if not file.filename.lower().endswith((".pdf", ".pptx", ".ppt")):
        raise HTTPException(400, "Only PDF or PowerPoint files are allowed")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds the 50 MB limit")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = os.path.basename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_filename}"
    storage_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(storage_path, "wb") as f:
        f.write(contents)

    doc = UploadedDocument(
        uploaded_by_user_id=user.id,
        subject_package_id=subject_package_id,
        chapter_id=chapter_id,
        filename=safe_filename,
        storage_path=storage_path,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    from app.workers.tasks import process_uploaded_document_task
    process_uploaded_document_task.delay(doc.id)

    return {"document_id": doc.id, "status": "processing"}


@router.get("/materials")
def list_materials(subject_package_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    _require_subject_access(db, user, subject_package_id)
    docs = (
        db.query(UploadedDocument)
        .filter(
            UploadedDocument.subject_package_id == subject_package_id,
            UploadedDocument.uploaded_by_user_id == user.id,
        )
        .order_by(UploadedDocument.created_at.desc())
        .all()
    )
    return {
        "documents": [
            {
                "id": d.id, "filename": d.filename, "chapter_id": d.chapter_id,
                "status": d.status, "chunk_count": d.chunk_count, "error_note": d.error_note,
            }
            for d in docs
        ]
    }


@router.get("/history")
def history(
    subject_package_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(StudyLog, Concept).join(Concept, Concept.id == StudyLog.concept_id).filter(
        StudyLog.user_id == user.id
    )
    if subject_package_id is not None:
        _require_subject_access(db, user, subject_package_id)
        query = query.filter(Concept.subject_package_id == subject_package_id)
    rows = query.order_by(StudyLog.created_at.desc()).limit(100).all()
    return {
        "items": [
            {
                "id": log.id,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "is_correct": log.is_correct,
                "attempt_number": log.attempt_number,
                "created_at": log.created_at,
            }
            for log, concept in rows
        ]
    }
