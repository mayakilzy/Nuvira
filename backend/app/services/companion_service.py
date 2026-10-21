"""
Companion service — كل منطق "الشخصية" الذي لا ينتمي لموجّه النظام مباشرة:
بنوك العبارات المتنوعة (لمنع الرتابة)، اختيار الأفاتار، توقيت الحقائق الطريفة،
وحساب الثقة/التكرار المتباعد.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.study import StudyLog, FunFactShownLog, AvatarState, PhraseUsage
from app.models.subject import Concept, FunFact


# ─────────────────────────────────────────────────────────────
# بنوك العبارات — 8 صياغات لكل حالة، بروح "أعزمك" الودّية المتفق عليها.
# {name} يُستبدل ديناميكياً باسم المستخدم الفعلي (full_name)، لا اسم ثابت.
# ─────────────────────────────────────────────────────────────
PHRASE_BANKS = {
    "break_invite": [
        "Wie wär's, {name} — ich lad dich auf einen virtuellen Saft ein, und danach machen wir weiter?",
        "Lass uns kurz Luft holen, {name}. Ein Kaffee, eine kleine Pause, dann sind wir wieder frisch.",
        "Ich glaub, dein Kopf braucht fünf Minuten Pause, {name}. Ich warte hier mit einem virtuellen Tee auf dich.",
        "{name}, wie wär's mit einer kurzen Pause? Ich lad dich auf ein virtuelles Stück Schokolade ein.",
        "Zeit für eine kleine Verschnaufpause, {name}. Wir machen gleich weiter, versprochen.",
        "Ich glaub, ein bisschen frische Luft würde dir jetzt gut tun, {name}. Ich bin hier, wenn du zurück bist.",
        "{name}, lass uns beide kurz durchatmen. Fünf Minuten, dann greifen wir das noch einmal an.",
        "Wie wär's mit einer Mini-Pause, {name}? Ich halte dir hier virtuell einen Platz frei.",
    ],
    "encouragement": [
        "{name}, du bist heute richtig in Fahrt! Weiter so?",
        "Drei Richtige hintereinander, {name} — du verstehst das wirklich. Lust auf noch eins?",
        "Das war eine saubere Antwort, {name}. Ich glaub, du bist bereit für die nächste Stufe.",
        "{name}, das läuft heute richtig gut bei dir. Machen wir weiter?",
        "Ich bin beeindruckt, {name} — das war nicht einfach, und du hast es verstanden.",
        "Das ging schnell und sicher, {name}. Willst du gleich weitermachen?",
        "{name}, du merkst es vielleicht selbst nicht, aber das war ein großer Schritt.",
        "Richtig gut, {name}! Genau so verankert sich das im Kopf.",
    ],
    "session_close": [
        "Heute hast du {concept} wirklich verstanden, {name} — nicht nur die Regel, sondern auch warum sie funktioniert. Bis nächstes Mal!",
        "Gute Session heute, {name}. {concept} sitzt jetzt viel sicherer als vorher.",
        "{name}, du hast heute einen echten Fortschritt gemacht bei {concept}. Bis bald!",
        "Das war eine solide Runde, {name}. {concept} ist jetzt ein Stück vertrauter geworden.",
        "Ich glaub, {concept} ist heute ein bisschen mehr 'deins' geworden, {name}. Bis zum nächsten Mal!",
        "{name}, schön gearbeitet heute. Wir machen genau hier weiter, wenn du zurückkommst.",
        "Ein guter Tag für {concept}, {name}. Ruh dich jetzt aus.",
        "Das hat sich gelohnt, {name}. {concept} bleibt jetzt länger hängen.",
    ],
    "fun_fact_intro": [
        "Übrigens, {name}, bevor wir weitermachen — weißt du, dass...",
        "Kleine Randnotiz, {name}: das hier ist wirklich interessant...",
        "{name}, das hier kannst du gleich deinen Freundinnen erzählen:",
        "Eine Sache noch, {name}, die die meisten nicht wissen:",
        "Warte, {name} — das hier ist zu gut, um es nicht zu erwähnen:",
        "{name}, kurzer Fun Fact zwischendurch:",
        "Das passt genau hierher, {name}:",
        "Bevor du weitermachst, {name} — check das hier:",
    ],
}


def pick_phrase(db: Session, user_id: int, category: str, **format_kwargs) -> str:
    """
    يختار عبارة من البنك المناسب، يتجنّب آخر عبارتين استُخدمتا لهذا المستخدم
    بهذي الفئة، ويسجّل الاستخدام الجديد.
    """
    bank = PHRASE_BANKS[category]
    recent = (
        db.query(PhraseUsage.phrase_index)
        .filter(PhraseUsage.user_id == user_id, PhraseUsage.category == category)
        .order_by(PhraseUsage.used_at.desc())
        .limit(2)
        .all()
    )
    recent_indices = {r[0] for r in recent}
    available = [i for i in range(len(bank)) if i not in recent_indices] or list(range(len(bank)))
    chosen_index = random.choice(available)

    db.add(PhraseUsage(user_id=user_id, category=category, phrase_index=chosen_index))
    db.commit()

    return bank[chosen_index].format(name=format_kwargs.get("name", ""), concept=format_kwargs.get("concept", ""))


# ─────────────────────────────────────────────────────────────
# الأفاتار — شكل/لون متبدّل كل جلسة (نظام معياري: شكل × لون منفصلين)
# ─────────────────────────────────────────────────────────────
def get_or_rotate_avatar(db: Session, user_id: int, session_key: str) -> dict:
    """
    يرجع شكل/لون الأفاتار الحالي. لو هذي "جلسة جديدة" (session_key مختلف عن آخر
    جلسة محفوظة)، يبدّل الشكل واللون عشوائياً من القائمة المفتوحة لهذا المستخدم.
    """
    state = db.query(AvatarState).filter(AvatarState.user_id == user_id).first()
    if not state:
        state = AvatarState(user_id=user_id, last_session_key=session_key)
        db.add(state)
        try:
            db.commit()
            db.refresh(state)
        except IntegrityError:
            # Two initial requests can race (for example React Strict Mode in
            # development). The unique user_id constraint chooses the winner;
            # reload that committed row instead of returning a 500.
            db.rollback()
            state = db.query(AvatarState).filter(AvatarState.user_id == user_id).first()
            if not state:
                raise
        return {"shape": state.current_shape, "color": state.current_color}

    if state.last_session_key != session_key:
        shapes = state.unlocked_shapes.split(",")
        colors = state.unlocked_colors.split(",")
        state.current_shape = random.choice(shapes)
        state.current_color = random.choice(colors)
        state.last_session_key = session_key
        db.commit()

    return {"shape": state.current_shape, "color": state.current_color}


# ─────────────────────────────────────────────────────────────
# التكرار المتباعد — مستوى ثقة 0-3، يرتفع بالنجاح، ينخفض درجة واحدة فقط
# (لا يُصفَّر أبداً)، لا يُعرض كرقم للمستخدم مطلقاً.
# ─────────────────────────────────────────────────────────────
REVIEW_INTERVALS_DAYS = {0: 1, 1: 3, 2: 7, 3: 14}  # مستوى الثقة -> بعد كم يوم يُعاد


def record_attempt(db: Session, user_id: int, concept_id: int, is_correct: bool,
                    attempt_number: int, session_note: str | None = None) -> dict:
    """يسجّل محاولة، يحدّث مستوى الثقة، ويرجع معلومات السلسلة (للتفعيل معايرة النغمة)."""
    last = (
        db.query(StudyLog)
        .filter(StudyLog.user_id == user_id, StudyLog.concept_id == concept_id)
        .order_by(StudyLog.created_at.desc())
        .first()
    )
    prev_confidence = last.confidence_level if last else 0

    if is_correct:
        new_confidence = min(prev_confidence + 1, 3)
    else:
        new_confidence = max(prev_confidence - 1, 0)  # درجة واحدة فقط، لا يصفّر أبداً

    db.add(StudyLog(
        user_id=user_id, concept_id=concept_id, is_correct=is_correct,
        confidence_level=new_confidence, attempt_number=attempt_number,
        session_note=session_note,
    ))
    db.commit()

    return {
        "confidence_level": new_confidence,
        "streak": _current_streak(db, user_id),
    }


def _current_streak(db: Session, user_id: int) -> dict:
    """يحسب السلسلة الحالية (صحيح متتالي أو خطأ متتالي) لتفعيل معايرة النغمة."""
    recent = (
        db.query(StudyLog.is_correct)
        .filter(StudyLog.user_id == user_id)
        .order_by(StudyLog.created_at.desc())
        .limit(5)
        .all()
    )
    if not recent:
        return {"type": None, "count": 0}

    first = recent[0][0]
    count = 0
    for (is_correct,) in recent:
        if is_correct == first:
            count += 1
        else:
            break
    return {"type": "correct" if first else "incorrect", "count": count}


def concepts_due_for_review(db: Session, user_id: int, subject_package_id: int) -> list[Concept]:
    """
    يرجع المفاهيم اللي 'تستاهل وقفة اليوم' حسب آخر محاولة وفاصلها الزمني —
    بدون أي رقم أو نسبة تُعرض، فقط قائمة داخلية يستخدمها الرفيق لاقتراح المراجعة.
    """
    due = []
    concepts = db.query(Concept).filter(Concept.subject_package_id == subject_package_id).all()
    for concept in concepts:
        last = (
            db.query(StudyLog)
            .filter(StudyLog.user_id == user_id, StudyLog.concept_id == concept.id)
            .order_by(StudyLog.created_at.desc())
            .first()
        )
        if not last:
            continue  # لم تُدرَس بعد — ليست "مراجعة"، بل محتوى جديد
        interval = REVIEW_INTERVALS_DAYS.get(last.confidence_level, 14)
        if datetime.now(last.created_at.tzinfo) - last.created_at >= timedelta(days=interval):
            due.append(concept)
    return due


# ─────────────────────────────────────────────────────────────
# "هل تعلم" — توقيت عشوائي غير متوقع، مرة واحدة بالجلسة، بدون تكرار
# ─────────────────────────────────────────────────────────────
CANDIDATE_MINUTES = [3, 5, 7, 10, 15]


def pick_fun_fact(db: Session, user_id: int, concept_id: int) -> dict | None:
    """يختار حقيقة طريفة لم تُعرض لهذا المستخدم بعد، مرتبطة بالمفهوم الحالي."""
    shown_ids = {
        row[0] for row in
        db.query(FunFactShownLog.fun_fact_id).filter(FunFactShownLog.user_id == user_id).all()
    }
    candidates = (
        db.query(FunFact)
        .filter(FunFact.concept_id == concept_id, ~FunFact.id.in_(shown_ids or [0]))
        .all()
    )
    if not candidates:
        return None
    fact = random.choice(candidates)
    return {"id": fact.id, "text": fact.text}


def mark_fun_fact_shown(db: Session, user_id: int, fun_fact_id: int, at_minute: int):
    db.add(FunFactShownLog(user_id=user_id, fun_fact_id=fun_fact_id, shown_at_minute=at_minute))
    db.commit()
