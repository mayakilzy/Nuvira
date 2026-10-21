"""
Central configuration. Every tunable value lives here and is read from the
environment (.env). Nothing in the rest of the codebase should read os.environ
directly — import `settings` instead.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "SaaS Template"
    ENV: str = "development"          # development | production
    DEBUG: bool = True
    API_PREFIX: str = ""              # e.g. "/api" if you want everything namespaced
    FRONTEND_URL: str = "http://localhost:3008"
    RATE_LIMIT_PER_MINUTE: int = 120  # per IP; 0 disables
    EMBEDDING_DIM: int = 1536  # vector size (match your embedding model)

    # --- Database (own Postgres, internal docker network) ---
    DATABASE_URL: str = "postgresql+psycopg2://saas:saas@db:5432/saas"

    # --- Auth / JWT ---
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8995/auth/google/callback"

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # --- Payments (provider-agnostic). Switch with one value. ---
    PAYMENT_PROVIDER: str = "lemonsqueezy"  # lemonsqueezy | paddle | stripe

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

    # --- Email (Resend) ---
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@example.com"

    # --- Admin bootstrap ---
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
