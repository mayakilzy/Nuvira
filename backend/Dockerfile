# ---- builder ----
FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---- runtime ----
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m appuser
COPY --from=builder /install /usr/local
COPY . .
# Writable private-content directories owned by the non-root runtime user
# (backend + worker share their named volumes). On first mount Docker copies
# each image directory's ownership/permissions onto the volume, so both must
# exist and be owned by appuser. 770 (not 777) prevents unrelated users in the
# container from writing student files or curriculum source documents.
RUN mkdir -p /app/uploads /app/curriculum-content \
    && chown appuser:appuser /app/uploads /app/curriculum-content \
    && chmod 770 /app/uploads /app/curriculum-content
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
