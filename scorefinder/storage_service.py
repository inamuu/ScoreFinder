from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import httpx

from .models import StoredFile
from .schemas import SaveScoreRequest
from .utils import guess_extension, is_remote_url, looks_like_sample, sanitize_component


HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    )
}


class StorageService:
    def __init__(self) -> None:
        self.timeout = 60.0

    def download(self, request: SaveScoreRequest, storage_root: str) -> StoredFile:
        if not is_remote_url(request.source_url):
            raise ValueError("保存対象 URL が不正です")
        if looks_like_sample(request.source_title, request.source_url, request.source_page_url):
            raise ValueError("sample と判断された候補は保存できません")

        base_root = Path(storage_root).expanduser().resolve()
        base_root.mkdir(parents=True, exist_ok=True)

        target_dir = (
            base_root
            / sanitize_component(request.artist)
            / sanitize_component(request.song_title)
            / sanitize_component(request.score_type)
        )
        target_dir.mkdir(parents=True, exist_ok=True)

        with httpx.stream(
            "GET",
            request.source_url,
            follow_redirects=True,
            timeout=self.timeout,
            headers=HTTP_HEADERS,
        ) as response:
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "").split(";")[0].lower()
            extension = guess_extension(str(response.url), mime_type, request.media_kind)
            if not self._matches_media_kind(request.media_kind, mime_type, extension):
                raise ValueError("取得したファイル形式が期待と異なります")
            filename = self._build_filename(request, extension)
            target_path = self._next_available_path(target_dir / filename)

            digest = hashlib.sha256()
            size = 0
            with target_path.open("wb") as output:
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)

        return StoredFile(
            path=target_path,
            filename=target_path.name,
            mime_type=mime_type or ("application/pdf" if request.media_kind == "pdf" else "image/jpeg"),
            extension=extension,
            media_kind=request.media_kind,
            file_size=size,
            sha256=digest.hexdigest(),
        )

    def store_html_document(
        self,
        request: SaveScoreRequest,
        storage_root: str,
        html_content: str,
    ) -> StoredFile:
        base_root = Path(storage_root).expanduser().resolve()
        base_root.mkdir(parents=True, exist_ok=True)

        target_dir = (
            base_root
            / sanitize_component(request.artist)
            / sanitize_component(request.song_title)
            / sanitize_component(request.score_type)
        )
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = self._build_filename(request, "html")
        target_path = self._next_available_path(target_dir / filename)
        encoded = html_content.encode("utf-8")
        target_path.write_bytes(encoded)

        digest = hashlib.sha256(encoded).hexdigest()
        return StoredFile(
            path=target_path,
            filename=target_path.name,
            mime_type="text/html",
            extension="html",
            media_kind="html",
            file_size=len(encoded),
            sha256=digest,
        )

    @staticmethod
    def _matches_media_kind(media_kind: str, mime_type: str, extension: str) -> bool:
        if media_kind == "html":
            return mime_type == "text/html" or extension in {"html", "htm"}
        if media_kind == "pdf":
            return mime_type == "application/pdf" or extension == "pdf"
        return mime_type.startswith("image/") or extension in {
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
            "bmp",
            "svg",
        }

    @staticmethod
    def _build_filename(request: SaveScoreRequest, extension: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        artist = sanitize_component(request.artist)
        song_title = sanitize_component(request.song_title)
        score_type = sanitize_component(request.score_type)
        return f"{artist}__{song_title}__{score_type}__{timestamp}.{extension}"

    @staticmethod
    def _next_available_path(path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        counter = 2
        while True:
            candidate = path.with_name(f"{stem}-{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1
