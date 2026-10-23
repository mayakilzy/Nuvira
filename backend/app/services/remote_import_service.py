"""HTTPS curriculum import with redirect-aware SSRF defenses and byte limits."""
from __future__ import annotations

import hashlib
import ipaddress
import socket
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx
from fastapi import HTTPException

from app.config import settings
from app.services.content_storage import LocalContentStorage, safe_filename


def validate_remote_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise HTTPException(400, "Remote curriculum imports require an HTTPS URL")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise HTTPException(400, "Remote URL credentials and non-HTTPS ports are not allowed")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise HTTPException(400, "Remote URL destination is prohibited")
    try:
        addresses = {entry[4][0].split("%", 1)[0] for entry in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise HTTPException(400, "Remote URL hostname could not be resolved") from exc
    if not addresses:
        raise HTTPException(400, "Remote URL hostname could not be resolved")
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise HTTPException(400, "Remote URL destination is prohibited")
    return url


async def fetch_pdf(url: str, storage: LocalContentStorage) -> tuple[Path, int, str, str, str]:
    current = validate_remote_url(url)
    temp = storage.create_temp()
    digest = hashlib.sha256()
    size = 0
    try:
        timeout = httpx.Timeout(
            settings.REMOTE_IMPORT_TIMEOUT_SECONDS,
            connect=settings.REMOTE_IMPORT_CONNECT_TIMEOUT_SECONDS,
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            for redirect_count in range(settings.REMOTE_IMPORT_MAX_REDIRECTS + 1):
                validate_remote_url(current)
                async with client.stream(
                    "GET", current, headers={"Accept": "application/pdf", "User-Agent": "Nuvira-Curriculum-Importer/1.0"}
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count >= settings.REMOTE_IMPORT_MAX_REDIRECTS:
                            raise HTTPException(400, "Remote import exceeded the redirect limit")
                        location = response.headers.get("location")
                        if not location:
                            raise HTTPException(400, "Remote import returned an invalid redirect")
                        current = validate_remote_url(urljoin(current, location))
                        continue
                    if response.status_code != 200:
                        raise HTTPException(400, f"Remote source returned HTTP {response.status_code}")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type not in {"application/pdf", "application/octet-stream"}:
                        raise HTTPException(400, "Remote source is not a supported PDF")
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > settings.CONTENT_MAX_FILE_BYTES:
                        raise HTTPException(413, "Remote curriculum source exceeds the configured size limit")
                    with temp.open("wb") as handle:
                        async for chunk in response.aiter_bytes(settings.CONTENT_UPLOAD_CHUNK_BYTES):
                            size += len(chunk)
                            if size > settings.CONTENT_MAX_FILE_BYTES:
                                raise HTTPException(413, "Remote curriculum source exceeds the configured size limit")
                            digest.update(chunk)
                            handle.write(chunk)
                    filename = safe_filename(Path(unquote(urlparse(current).path)).name or "remote-source.pdf")
                    return temp, size, digest.hexdigest(), current, filename
        raise HTTPException(400, "Remote import failed")
    except Exception:
        temp.unlink(missing_ok=True)
        raise
