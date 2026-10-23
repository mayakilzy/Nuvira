"""Private curriculum binary storage with streaming, checksums and deduplication."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    original_filename: str
    mime_type: str
    size: int
    sha256: str


def safe_filename(filename: str | None) -> str:
    base = os.path.basename(filename or "source.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(". ")
    return (cleaned[:180] or "source.pdf")


def validate_pdf_signature(path: Path, content_type: str | None = None) -> str:
    if content_type and content_type.split(";", 1)[0].strip().lower() not in {
        "application/pdf", "application/octet-stream"
    }:
        raise HTTPException(400, "Only PDF curriculum sources are supported")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise HTTPException(400, "File content does not match PDF format")
    return "application/pdf"


class LocalContentStorage:
    """Filesystem implementation; storage keys remain portable to an S3 backend."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.CONTENT_STORAGE_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ".incoming").mkdir(exist_ok=True)

    def create_temp(self) -> Path:
        descriptor, name = tempfile.mkstemp(prefix="curriculum-", suffix=".part", dir=self.root / ".incoming")
        os.close(descriptor)
        return Path(name)

    async def receive_upload(self, upload: UploadFile) -> tuple[Path, int, str]:
        temp = self.create_temp()
        digest = hashlib.sha256()
        size = 0
        try:
            with temp.open("wb") as handle:
                while chunk := await upload.read(settings.CONTENT_UPLOAD_CHUNK_BYTES):
                    size += len(chunk)
                    if size > settings.CONTENT_MAX_FILE_BYTES:
                        raise HTTPException(413, "Curriculum source exceeds the configured size limit")
                    digest.update(chunk)
                    handle.write(chunk)
            return temp, size, digest.hexdigest()
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    def finalize(self, temp: Path, checksum: str, filename: str, mime_type: str) -> StoredObject:
        suffix = ".pdf" if mime_type == "application/pdf" else Path(filename).suffix.lower()
        key = f"sha256/{checksum[:2]}/{checksum}{suffix}"
        destination = (self.root / key).resolve()
        if self.root not in destination.parents:
            raise ValueError("Unsafe storage key")
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = temp.stat().st_size
        if destination.exists():
            temp.unlink(missing_ok=True)
        else:
            os.replace(temp, destination)
        return StoredObject(key, safe_filename(filename), mime_type, size, checksum)

    def path_for(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if self.root not in path.parents or not path.is_file():
            raise FileNotFoundError(storage_key)
        return path

    def remove(self, storage_key: str) -> None:
        try:
            self.path_for(storage_key).unlink(missing_ok=True)
        except FileNotFoundError:
            return


def get_content_storage() -> LocalContentStorage:
    if settings.CONTENT_STORAGE_BACKEND != "local":
        raise RuntimeError("Configured content storage backend is not implemented")
    return LocalContentStorage()


def copy_into_temp(source: Path, storage: LocalContentStorage) -> tuple[Path, int, str]:
    """Streaming helper used by controlled server-side import paths."""
    temp = storage.create_temp()
    digest = hashlib.sha256()
    size = 0
    try:
        with source.open("rb") as reader, temp.open("wb") as writer:
            while chunk := reader.read(settings.CONTENT_UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > settings.CONTENT_MAX_FILE_BYTES:
                    raise HTTPException(413, "Curriculum source exceeds the configured size limit")
                digest.update(chunk)
                writer.write(chunk)
        return temp, size, digest.hexdigest()
    except Exception:
        temp.unlink(missing_ok=True)
        raise
