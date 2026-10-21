"""
Application entrypoint.

/health does NOT touch the database, so it answers even before Postgres is ready
(used by Docker healthchecks). /health/db checks the actual DB connection.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.routers import auth, billing, credits, user, admin, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enable pgvector (PostgreSQL only) BEFORE creating tables that use Vector.
    try:
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
    except Exception as e:
        print(f"[startup] vector extension: {e}")
    # create_all is idempotent (creates only missing tables); safe on every boot.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[startup] create_all: {e}")
    # Seed default plans + first admin (idempotent).
    try:
        from app.core.seed import seed
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[seed] skipped: {e}")
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

from app.core.ratelimit import RateLimitMiddleware, SecurityHeadersMiddleware  # noqa: E402
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

allowed_origins = [settings.FRONTEND_URL]
if settings.EXTRA_CORS_ORIGINS:
    allowed_origins.extend(
        origin.strip()
        for origin in settings.EXTRA_CORS_ORIGINS.split(",")
        if origin.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, billing.router, credits.router, user.router, admin.router, agent.router):
    app.include_router(r, prefix=settings.API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}


@app.get("/health/db")
def health_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception as e:
        return {"database": "error", "detail": str(e)[:200]}
