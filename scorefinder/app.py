from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from .config import (
    AppConfig,
    ensure_database_location,
    get_bootstrap_path,
    get_config_path,
    load_config,
    save_config,
)
from .database import ScoreRepository
from .import_service import ScoreImportService
from .schemas import ConfigUpdate, SaveScoreRequest
from .search_service import HTTP_HEADERS as SEARCH_HEADERS
from .search_service import RemoteSearchService
from .storage_service import StorageService
from .utils import is_remote_url


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
SCORE_TYPES = ("コード譜", "タブ譜", "五線譜", "メロディ譜", "その他")


def create_app() -> FastAPI:
    app = FastAPI(title="ScoreFinder")
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    app.state.repository = None
    app.state.repository_db_path = None
    app.state.search_service = RemoteSearchService()
    app.state.import_service = ScoreImportService()
    app.state.storage_service = StorageService()
    _get_repository(app)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "score_types": SCORE_TYPES,
            },
        )

    @app.get("/api/config")
    def get_config() -> dict[str, str]:
        config = load_config()
        database_path = str(ensure_database_location(config))
        config_path = str(get_config_path(config))
        return {
            "storage_root": config.storage_root,
            "config_path": config_path,
            "bootstrap_path": str(get_bootstrap_path()),
            "database_path": database_path,
        }

    @app.post("/api/config")
    def update_config(payload: ConfigUpdate) -> dict[str, str]:
        previous_config = load_config()
        try:
            config = save_config(AppConfig(storage_root=payload.storage_root))
            database_path = str(
                ensure_database_location(config, previous_storage_root=previous_config.storage_root)
            )
            _get_repository(app, config)
        except OSError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "storage_root": config.storage_root,
            "config_path": str(get_config_path(config)),
            "bootstrap_path": str(get_bootstrap_path()),
            "database_path": database_path,
        }

    @app.get("/api/import")
    def import_score(url: str = Query(min_length=1)) -> dict[str, Any]:
        try:
            payload = app.state.import_service.import_url(url)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=f"URL 取り込みに失敗しました: {error}") from error
        return payload

    @app.get("/api/search/remote")
    def search_remote(
        query: str = Query(min_length=1),
        limit: int = Query(default=18, ge=1, le=30),
    ) -> dict[str, Any]:
        try:
            payload = app.state.search_service.search(query, limit=limit)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"外部検索に失敗しました: {error}") from error

        payload["results"] = [_serialize_remote_result(item) for item in payload["results"]]
        return payload

    @app.post("/api/scores")
    def save_score(payload: SaveScoreRequest) -> dict[str, Any]:
        config = load_config()
        repository = _get_repository(app, config)
        try:
            if payload.media_kind == "html":
                imported = app.state.import_service.import_url(payload.source_url)
                stored_file = app.state.storage_service.store_html_document(
                    payload,
                    config.storage_root,
                    str(imported["preview_html"]),
                )
            else:
                stored_file = app.state.storage_service.download(payload, config.storage_root)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=f"ファイル取得に失敗しました: {error}") from error

        score = repository.insert_score(payload, stored_file)
        return _serialize_saved_score(score)

    @app.get("/api/scores")
    def search_saved_scores(
        q: str | None = None,
        artist: str | None = None,
        song_title: str | None = None,
        score_type: str | None = None,
        media_kind: str | None = Query(default=None, pattern="^(image|pdf|html)$"),
        saved_from: str | None = None,
        saved_to: str | None = None,
    ) -> dict[str, Any]:
        repository = _get_repository(app)
        try:
            scores = repository.search_scores(
                q=q,
                artist=artist,
                song_title=song_title,
                score_type=score_type,
                media_kind=media_kind,
                saved_from=_parse_date(saved_from),
                saved_to=_parse_date(saved_to),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return {"results": [_serialize_saved_score(score) for score in scores]}

    @app.get("/api/scores/{score_id}")
    def get_score(score_id: int) -> dict[str, Any]:
        repository = _get_repository(app)
        try:
            score = repository.get_score(score_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="保存済み楽譜が見つかりません") from error
        return _serialize_saved_score(score)

    @app.get("/api/scores/{score_id}/content")
    def get_score_content(score_id: int) -> FileResponse:
        repository = _get_repository(app)
        try:
            score = repository.get_score(score_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="保存済み楽譜が見つかりません") from error

        file_path = Path(score["storage_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="保存ファイルが見つかりません")

        return FileResponse(
            path=file_path,
            media_type=score["mime_type"],
            filename=score["storage_filename"],
            content_disposition_type="inline",
        )

    @app.get("/api/preview")
    def preview_remote(url: str = Query(min_length=1)) -> StreamingResponse:
        if not is_remote_url(url):
            raise HTTPException(status_code=400, detail="プレビュー URL が不正です")

        stream = httpx.stream(
            "GET",
            url,
            follow_redirects=True,
            timeout=30.0,
            headers=SEARCH_HEADERS,
        )
        try:
            remote = stream.__enter__()
            remote.raise_for_status()
        except httpx.HTTPError as error:
            stream.__exit__(None, None, None)
            raise HTTPException(status_code=502, detail=f"プレビュー取得に失敗しました: {error}") from error

        media_type = remote.headers.get("content-type", "").split(";")[0] or "application/octet-stream"
        return StreamingResponse(
            remote.iter_bytes(),
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
            background=BackgroundTask(stream.__exit__, None, None, None),
        )

    @app.get("/health")
    def healthcheck() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


def _get_repository(app: FastAPI, config: AppConfig | None = None) -> ScoreRepository:
    resolved_config = config or load_config()
    db_path = ensure_database_location(resolved_config)
    current_repository = getattr(app.state, "repository", None)
    current_db_path = getattr(app.state, "repository_db_path", None)
    if current_repository is None or current_db_path != db_path:
        repository = ScoreRepository(db_path)
        repository.initialize()
        app.state.repository = repository
        app.state.repository_db_path = db_path
    return app.state.repository


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        from datetime import date

        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("日付は YYYY-MM-DD 形式で指定してください") from error


def _serialize_remote_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **item,
        "preview_url": f"/api/preview?url={quote(item['source_url'], safe='')}",
    }


def _serialize_saved_score(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **item,
        "content_url": f"/api/scores/{item['id']}/content",
    }


app = create_app()


def main() -> None:
    import uvicorn

    host = os.environ.get("SCOREFINDER_HOST", "127.0.0.1")
    port = int(os.environ.get("SCOREFINDER_PORT", "8000"))
    uvicorn.run("scorefinder.app:app", host=host, port=port, reload=False)
