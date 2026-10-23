"""Deterministic, retry-safe extraction of draft lessons from curriculum PDFs."""
from __future__ import annotations

import logging

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.content import Chapter
from app.models.curriculum import CurriculumUnit, LearningResource, Lesson
from app.models.subject import Concept
from app.services.content_storage import get_content_storage


def _lesson_pages(page_texts: list[str]) -> list[tuple[int, str]]:
    def marker(line: str) -> bool:
        folded = line.casefold()
        return (
            ("الدرس" in line and "الوحدة" in line)
            or ("سردلا" in line and "ةدحولا" in line)
            or ("lesson" in folded and "unit" in folded)
            or ("lektion" in folded and ("einheit" in folded or "kapitel" in folded))
        )
    marked = [
        (index, text) for index, text in enumerate(page_texts, start=1)
        if any(marker(line) for line in text.splitlines()[:6])
    ]
    if marked:
        return marked
    if len(page_texts) > 2:
        return [(index, text) for index, text in enumerate(page_texts[1:-1], start=2) if text.strip()]
    return [(index, text) for index, text in enumerate(page_texts, start=1) if text.strip()]


def _draft_title(text: str, page_number: int) -> str:
    lines = [line.strip(" •") for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines[:8]):
        if ("الدرس" in line or "سردلا" in line or "lesson" in line.casefold() or "lektion" in line.casefold()) and index + 1 < len(lines):
            return lines[index + 1][:255]
    return (lines[0][:255] if lines else f"Imported lesson - page {page_number}")


def _sections(text: str, logical: str, reversed_word: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if logical in line or reversed_word in line]


def process_resource(db: Session, resource_id: int) -> None:
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        return
    if resource.processing_status == "review" and db.query(Lesson).filter(Lesson.learning_resource_id == resource.id).count():
        return
    try:
        resource.processing_attempts += 1
        resource.processing_status = "processing"
        resource.reviewed_at = None
        resource.error_code = None
        resource.error_note = None
        db.commit()

        path = get_content_storage().path_for(resource.storage_key)
        reader = PdfReader(str(path))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        candidates = _lesson_pages(page_texts)
        if not candidates:
            raise ValueError("No extractable lesson text")

        db.query(Concept).filter(Concept.lesson_id.in_(
            db.query(Lesson.id).filter(Lesson.learning_resource_id == resource.id)
        )).delete(synchronize_session=False)
        db.query(Lesson).filter(Lesson.learning_resource_id == resource.id).delete(synchronize_session=False)
        db.query(Chapter).filter(Chapter.learning_resource_id == resource.id).delete(synchronize_session=False)
        db.query(CurriculumUnit).filter(CurriculumUnit.learning_resource_id == resource.id).delete(synchronize_session=False)
        db.flush()

        unit = CurriculumUnit(
            subject_package_id=resource.subject_package_id,
            learning_resource_id=resource.id,
            title="Imported unit - review required",
            order_index=1,
        )
        db.add(unit)
        db.flush()
        chapter = Chapter(
            subject_package_id=resource.subject_package_id,
            learning_resource_id=resource.id,
            unit_id=unit.id,
            chapter_number=1,
            title="Imported chapter - review required",
        )
        db.add(chapter)
        db.flush()

        for order, (page_number, text) in enumerate(candidates, start=1):
            title = _draft_title(text, page_number)
            lesson = Lesson(
                subject_package_id=resource.subject_package_id,
                learning_resource_id=resource.id,
                unit_id=unit.id,
                chapter_id=chapter.id,
                title=title,
                content_language=resource.content_language,
                order_index=order,
                page_start=page_number,
                page_end=page_number,
                content_text=text,
                examples_json=_sections(text, "مثال", "لاثم"),
                exercises_json=_sections(text, "تمرين", "نيرمت"),
                publication_status="review",
            )
            db.add(lesson)
            db.flush()
            db.add(Concept(
                subject_package_id=resource.subject_package_id,
                chapter_id=chapter.id,
                lesson_id=lesson.id,
                order_index=1,
                name=title,
                everyday_analogy=(text[:500] or None),
                difficulty=1,
                official_source_note=f"{resource.title}, page {page_number}",
            ))

        resource.processing_status = "review"
        resource.publication_status = "review"
        db.commit()
    except Exception:
        logging.exception("Curriculum resource processing failed", extra={"resource_id": resource_id})
        db.rollback()
        resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
        if resource:
            resource.processing_status = "failed"
            resource.error_code = "CURRICULUM_EXTRACTION_FAILED"
            resource.error_note = "Extraction failed. Retry the import or review the source file."
            db.commit()
        raise
