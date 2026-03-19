from __future__ import annotations

import mimetypes
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse


SAMPLE_MARKERS = (
    "sample",
    "samples",
    "preview",
    "watermark",
    "demo",
    "サンプル",
)

SCORE_HINTS = (
    "楽譜",
    "コード譜",
    "コード",
    "タブ譜",
    "tab",
    "tabs",
    "tablature",
    "sheet music",
    "score",
    "pdf",
)

INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
MULTIPLE_UNDERSCORES_RE = re.compile(r"_+")


def looks_like_sample(*values: str | None) -> bool:
    merged = " ".join(value for value in values if value).lower()
    return any(marker in merged for marker in SAMPLE_MARKERS)


def normalize_search_query(query: str) -> str:
    stripped = query.strip()
    lowered = stripped.lower()
    if any(hint in lowered for hint in SCORE_HINTS):
        return stripped
    return f"{stripped} 楽譜"


def sanitize_component(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    compact = re.sub(r"\s+", "_", normalized)
    sanitized = INVALID_PATH_CHARS_RE.sub("_", compact)
    sanitized = MULTIPLE_UNDERSCORES_RE.sub("_", sanitized).strip(" ._")
    return sanitized or "untitled"


def guess_extension(url: str, mime_type: str | None, media_kind: str) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower().lstrip(".")
    if suffix:
        return suffix

    if mime_type:
        guessed = mimetypes.guess_extension(mime_type, strict=False)
        if guessed:
            return guessed.lstrip(".")

    return "pdf" if media_kind == "pdf" else "jpg"


def is_remote_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
