"""Stream uploads to a temp file while hashing, enforcing a size limit."""

import hashlib
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".ts", ".3gp"}


@dataclass(slots=True)
class StoredUpload:
    path: Path
    sha256: str
    size: int
    filename: str


@contextmanager
def stored_upload(upload: UploadFile, max_mb: int) -> Iterator[StoredUpload]:
    filename = Path(upload.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{suffix or 'none'}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    limit = max_mb * 1024 * 1024
    digest = hashlib.sha256()
    size = 0
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="dashcam-")
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := upload.file.read(1 << 20):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"File exceeds the {max_mb} MB limit",
                    )
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
        yield StoredUpload(Path(tmp), digest.hexdigest(), size, filename)
    finally:
        with suppress(OSError):
            os.remove(tmp)
