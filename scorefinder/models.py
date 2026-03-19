from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class StoredFile:
    path: Path
    filename: str
    mime_type: str
    extension: str
    media_kind: str
    file_size: int
    sha256: str
