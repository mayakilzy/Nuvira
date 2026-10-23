"""
Central configuration. Every tunable value lives here and is read from the
environment (.env). Nothing in the rest of the codebase should read os.environ
directly — import `settings` instead.
"""
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "Nuvira"
    ENV: str = "development"          # development | staging | production
    DEBUG: bool = True
    API_PREFIX: str = ""              # e.g. "/api" if you want everything namespaced
    FRONTEND_URL: str = "https://nuvira.agentcraft.info"
    EXTRA_CORS_ORIGINS: str = ""
    RATE_LIMIT_PER_MINUTE: int = 120  # per IP; 0 disables
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10
    TRUSTED_PROXY_IPS: str = ""
    EMBEDDING_DIM: int = 1536  # vector size (match your embedding model)

    # --- Database (own Postgres, internal docker network) ---
    DATABASE_URL: str = "postgresql+psycopg2://saas:saas@db:5432/saas"

    # --- Auth / JWT ---
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_COOKIE_NAME: str = "nuvira_refresh"

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8995/auth/google/callback"
    GOOGLE_OAUTH_ENABLED: bool = False

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # --- Payments (provider-agnostic). Switch with one value. ---
    PAYMENT_PROVIDER: str = "lemonsqueezy"  # lemonsqueezy | paddle | stripe
    PAYMENTS_ENABLED: bool = False

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # Lemon Squeezy (Merchant of Record — default)
    LEMONSQUEEZY_API_KEY: str = ""
    LEMONSQUEEZY_STORE_ID: str = ""
    LEMONSQUEEZY_WEBHOOK_SECRET: str = ""

    # Paddle Billing (Merchant of Record)
    PADDLE_API_KEY: str = ""
    PADDLE_WEBHOOK_SECRET: str = ""
    PADDLE_ENV: str = "sandbox"  # sandbox | production

    # --- AI layer (OpenRouter — model-agnostic) ---
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"  # changeable per project
    OPENAI_API_KEY: str = ""  # منفصل عن OPENROUTER — فقط لتوليد embeddings
    EMBEDDING_PROVIDER: str = "openai"  # openai | deterministic-test (staging only)
    AI_ENABLED: bool = False

    # --- Email (Resend) ---
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@example.com"
    EMAIL_ENABLED: bool = False

    # --- Admin bootstrap ---
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe123!"
    FIRST_ADMIN_ENABLED: bool = False

    # --- Upload protection ---
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024
    MAX_UPLOAD_BYTES_PER_USER: int = 250 * 1024 * 1024
    MAX_UPLOAD_FILES_PER_USER: int = 50
    MAX_ARCHIVE_ENTRIES: int = 500
    MAX_ARCHIVE_UNCOMPRESSED_BYTES: int = 100 * 1024 * 1024
    UPLOADS_ENABLED: bool = False

    # --- Curriculum library (private binaries live outside source/images) ---
    CONTENT_STORAGE_BACKEND: str = "local"  # local; S3-compatible adapter is a future backend
    CONTENT_STORAGE_ROOT: str = "/app/curriculum-content"
    CONTENT_MAX_FILE_BYTES: int = 256 * 1024 * 1024
    CONTENT_STORAGE_QUOTA_BYTES: int = 10 * 1024 * 1024 * 1024
    CONTENT_UPLOAD_CHUNK_BYTES: int = 1024 * 1024
    REMOTE_IMPORT_TIMEOUT_SECONDS: float = 60.0
    REMOTE_IMPORT_CONNECT_TIMEOUT_SECONDS: float = 10.0
    REMOTE_IMPORT_MAX_REDIRECTS: int = 3
    DEV_CURRICULUM_ENROLLMENT_ENABLED: bool = False

    @model_validator(mode="after")
    def validate_security_posture(self):
        if self.JWT_ALGORITHM != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        if self.ENV in {"staging", "production"}:
            errors: list[str] = []
            if self.EMBEDDING_DIM != 1536:
                errors.append("EMBEDDING_DIM must match the migrated vector dimension of 1536")
            if self.DEBUG:
                errors.append("DEBUG must be false")
            if "change_me" in self.JWT_SECRET.lower() or len(self.JWT_SECRET) < 64:
                errors.append("JWT_SECRET must be a non-placeholder value of at least 64 characters")
            if self.FIRST_ADMIN_ENABLED and (
                not self.FIRST_ADMIN_EMAIL
                or self.FIRST_ADMIN_EMAIL == "admin@example.com"
                or self.FIRST_ADMIN_PASSWORD == "ChangeMe123!"
                or len(self.FIRST_ADMIN_PASSWORD) < 14
            ):
                errors.append("FIRST_ADMIN credentials are unsafe")
            if self.GOOGLE_OAUTH_ENABLED and not all(
                (self.GOOGLE_CLIENT_ID, self.GOOGLE_CLIENT_SECRET, self.GOOGLE_REDIRECT_URI)
            ):
                errors.append("Google OAuth is enabled but incomplete")
            if self.PAYMENTS_ENABLED:
                required = {
                    "stripe": (self.STRIPE_SECRET_KEY, self.STRIPE_WEBHOOK_SECRET),
                    "lemonsqueezy": (
                        self.LEMONSQUEEZY_API_KEY,
                        self.LEMONSQUEEZY_STORE_ID,
                        self.LEMONSQUEEZY_WEBHOOK_SECRET,
                    ),
                    "paddle": (self.PADDLE_API_KEY, self.PADDLE_WEBHOOK_SECRET),
                }
                if self.PAYMENT_PROVIDER not in required or not all(required.get(self.PAYMENT_PROVIDER, ())):
                    errors.append("Active payment provider configuration is incomplete")
            if self.AI_ENABLED and not self.OPENROUTER_API_KEY:
                errors.append("AI is enabled but OPENROUTER_API_KEY is missing")
            if self.EMBEDDING_PROVIDER not in {"openai", "deterministic-test"}:
                errors.append("EMBEDDING_PROVIDER must be openai or deterministic-test")
            if self.ENV == "production" and self.EMBEDDING_PROVIDER != "openai":
                errors.append("production must use the openai embedding provider")
            if self.EMAIL_ENABLED and not self.RESEND_API_KEY:
                errors.append("Email is enabled but RESEND_API_KEY is missing")
            if self.CONTENT_STORAGE_BACKEND != "local":
                errors.append("CONTENT_STORAGE_BACKEND must be local until an object-storage adapter is configured")
            if self.ENV == "production" and self.DEV_CURRICULUM_ENROLLMENT_ENABLED:
                errors.append("development curriculum enrollment must be disabled in production")
            if errors:
                raise ValueError("Unsafe managed-environment configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
