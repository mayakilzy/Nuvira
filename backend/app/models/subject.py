"""
Subject content models — قابلة للتوسع لمواد ومستخدمين آخرين (مبدأ subject_package_id
بدل مبدأ tenant_id، كما اتفقنا: نفس الآلية، محورها "المادة" لا "المؤسسة").
"""
from datetime import datetime
from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, ForeignKey, JSON, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SubjectPackage(Base):
    """حزمة مادة كاملة (مثل: الكيمياء العضوية — جامعة فيينا)."""
    __tablename__ = "subject_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    curriculum_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("curriculum_versions.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    university: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), default="de")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    publication_status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    price_usd: Mapped[float | None] = mapped_column()
    # هل المحتوى تمت مراجعته من مصدر أكاديمي رسمي (سيناريو البروفيسور الذي ناقشناه)
    review_status: Mapped[str] = mapped_column(String(20), default="unreviewed")
    # unreviewed | self_reviewed | officially_reviewed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSubjectAccess(Base):
    """من يملك حق الوصول لأي حزمة — يفتح باب حسابات متعددة (ريفانا، مواد أخرى)."""
    __tablename__ = "user_subject_access"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_package_id", name="uq_user_subject_access"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    subject_package_id: Mapped[int] = mapped_column(ForeignKey("subject_packages.id"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="gifted")  # purchase | gifted | trial
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Concept(Base):
    """مفهوم كيميائي واحد: التشبيه، بيانات الآلية، درجة الصعوبة."""
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_package_id: Mapped[int] = mapped_column(ForeignKey("subject_packages.id"), index=True, nullable=False)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # مثل "SN2"
    everyday_analogy: Mapped[str | None] = mapped_column(Text)  # التشبيه من الحياة اليومية
    mechanism_json: Mapped[dict | None] = mapped_column(JSON)  # خطوات آلية التفاعل (نفس بنية الديمو)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    official_source_note: Mapped[str | None] = mapped_column(Text)  # مرجع من منهج الجامعة الرسمي
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FunFact(Base):
    """بنك 'هل تعلم' — مرتبط بمفهوم، وقابل للمشاركة اجتماعياً."""
    __tablename__ = "fun_facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
