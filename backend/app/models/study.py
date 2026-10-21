"""
Study/engagement models — الذاكرة طويلة المدى، التكرار المتباعد، الأفاتار،
وتتبع العبارات لمنع التكرار الممل.
"""
from datetime import datetime
from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class StudyLog(Base):
    """كل محاولة على مفهوم — أساس الذاكرة طويلة المدى + التكرار المتباعد الصامت."""
    __tablename__ = "study_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # مستوى الثقة بعد هذه المحاولة (0-3) — يرتفع تدريجياً، ينخفض درجة واحدة فقط، لا يُصفَّر أبداً
    confidence_level: Mapped[int] = mapped_column(Integer, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)  # 1، 2، أو 3 (حسب نظام التلميح التدريجي)
    session_note: Mapped[str | None] = mapped_column(Text)  # مثل "احتاجت 3 محاولات على الأسترة"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FunFactShownLog(Base):
    """أي 'هل تعلم' عُرضت ومتى — لضمان عدم التكرار وعشوائية التوقيت."""
    __tablename__ = "fun_fact_shown_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    fun_fact_id: Mapped[int] = mapped_column(ForeignKey("fun_facts.id"), index=True, nullable=False)
    shown_at_minute: Mapped[int] = mapped_column(Integer)  # الدقيقة بالجلسة التي عُرضت فيها
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AvatarState(Base):
    """شكل/لون الأفاتار الحالي للمستخدم، والقائمة المفتوحة له."""
    __tablename__ = "avatar_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    current_shape: Mapped[str] = mapped_column(String(30), default="leaf")  # leaf | molecule | droplet | sprout
    current_color: Mapped[str] = mapped_column(String(30), default="blue")
    last_session_key: Mapped[str | None] = mapped_column(String(64))  # لمعرفة "جلسة جديدة" وتبديل الشكل
    unlocked_shapes: Mapped[str] = mapped_column(Text, default="leaf,molecule,droplet,sprout")  # مفصولة بفواصل
    unlocked_colors: Mapped[str] = mapped_column(Text, default="blue,purple,green,coral")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PhraseUsage(Base):
    """تتبع آخر العبارات المستخدمة لكل مستخدم/فئة — يمنع تكرار نفس الصياغة جلستين متتاليتين."""
    __tablename__ = "phrase_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    # encouragement | break_invite | session_close | fun_fact_intro
    phrase_index: Mapped[int] = mapped_column(Integer, nullable=False)  # فهرس العبارة بالبنك
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
