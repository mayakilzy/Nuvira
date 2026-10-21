"""
User preferences — واجهة المستخدم (لغة العرض، المظهر)، منفصلة تماماً عن
لغة التدريس (التي تُحدَّد بحقل subject_packages.language، لا هنا).
"""
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    ui_language: Mapped[str] = mapped_column(String(5), default="de")  # de | en | ar
    theme: Mapped[str] = mapped_column(String(10), default="system")  # light | dark | system
    avatar_corner_enabled: Mapped[bool] = mapped_column(default=True)  # خيار تصغيره مؤقتاً
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserApiKey(Base):
    """
    بنية جاهزة لخيار 'أضف مفتاحك الخاص' (BYOK) — للاستثمار التجاري المستقبلي.
    غير مُفعَّلة بمنطق فعلي الآن، فقط الجدول موجود حتى لا نحتاج إعادة هيكلة لاحقاً.
    """
    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(30))  # openrouter | openai | anthropic
    encrypted_key: Mapped[str] = mapped_column(String(500))  # TODO: تشفير فعلي قبل التفعيل التجاري
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
