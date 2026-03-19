from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .models import StoredFile
from .schemas import SaveScoreRequest


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    artist TEXT NOT NULL,
    song_title TEXT NOT NULL,
    score_type TEXT NOT NULL,
    memo TEXT,
    media_kind TEXT NOT NULL CHECK(media_kind IN ('image', 'pdf', 'html')),
    mime_type TEXT NOT NULL,
    extension TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    storage_filename TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_page_url TEXT,
    source_title TEXT,
    provider TEXT,
    file_size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_scores_artist ON scores (artist);
CREATE INDEX IF NOT EXISTS idx_scores_song_title ON scores (song_title);
CREATE INDEX IF NOT EXISTS idx_scores_score_type ON scores (score_type);
CREATE INDEX IF NOT EXISTS idx_scores_media_kind ON scores (media_kind);
CREATE INDEX IF NOT EXISTS idx_scores_saved_at ON scores (saved_at);
"""

COLUMN_LIST = (
    "id",
    "query",
    "artist",
    "song_title",
    "score_type",
    "memo",
    "media_kind",
    "mime_type",
    "extension",
    "storage_path",
    "storage_filename",
    "source_url",
    "source_page_url",
    "source_title",
    "provider",
    "file_size",
    "sha256",
    "saved_at",
)


class ScoreRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            table_sql_row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'scores'"
            ).fetchone()
            if table_sql_row is None:
                connection.executescript(CREATE_TABLE_SQL)
            else:
                table_sql = table_sql_row["sql"] or ""
                if "'html'" not in table_sql:
                    self._migrate_scores_table(connection)

            connection.executescript(INDEX_SQL)

    def insert_score(self, request: SaveScoreRequest, stored_file: StoredFile) -> dict[str, Any]:
        saved_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO scores (
                    query,
                    artist,
                    song_title,
                    score_type,
                    memo,
                    media_kind,
                    mime_type,
                    extension,
                    storage_path,
                    storage_filename,
                    source_url,
                    source_page_url,
                    source_title,
                    provider,
                    file_size,
                    sha256,
                    saved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.query.strip(),
                    request.artist.strip(),
                    request.song_title.strip(),
                    request.score_type.strip(),
                    (request.memo or "").strip() or None,
                    stored_file.media_kind,
                    stored_file.mime_type,
                    stored_file.extension,
                    str(stored_file.path),
                    stored_file.filename,
                    request.source_url,
                    request.source_page_url,
                    request.source_title,
                    request.provider,
                    stored_file.file_size,
                    stored_file.sha256,
                    saved_at,
                ),
            )
            score_id = cursor.lastrowid
        return self.get_score(score_id)

    def get_score(self, score_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM scores WHERE id = ?",
                (score_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"score not found: {score_id}")
        return self._row_to_dict(row)

    def search_scores(
        self,
        *,
        q: str | None = None,
        artist: str | None = None,
        song_title: str | None = None,
        score_type: str | None = None,
        media_kind: str | None = None,
        saved_from: date | None = None,
        saved_to: date | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if q:
            clauses.append(
                "("
                "query LIKE ? OR "
                "artist LIKE ? OR "
                "song_title LIKE ? OR "
                "score_type LIKE ? OR "
                "source_title LIKE ? OR "
                "memo LIKE ?"
                ")"
            )
            like = f"%{q.strip()}%"
            params.extend([like, like, like, like, like, like])

        if artist:
            clauses.append("artist LIKE ?")
            params.append(f"%{artist.strip()}%")

        if song_title:
            clauses.append("song_title LIKE ?")
            params.append(f"%{song_title.strip()}%")

        if score_type:
            clauses.append("score_type = ?")
            params.append(score_type.strip())

        if media_kind:
            clauses.append("media_kind = ?")
            params.append(media_kind.strip())

        if saved_from:
            clauses.append("date(saved_at) >= date(?)")
            params.append(saved_from.isoformat())

        if saved_to:
            clauses.append("date(saved_at) <= date(?)")
            params.append(saved_to.isoformat())

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM scores {where} ORDER BY saved_at DESC, id DESC"

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate_scores_table(self, connection: sqlite3.Connection) -> None:
        columns = ", ".join(COLUMN_LIST)
        connection.executescript(
            f"""
            CREATE TABLE scores_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                artist TEXT NOT NULL,
                song_title TEXT NOT NULL,
                score_type TEXT NOT NULL,
                memo TEXT,
                media_kind TEXT NOT NULL CHECK(media_kind IN ('image', 'pdf', 'html')),
                mime_type TEXT NOT NULL,
                extension TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                storage_filename TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_page_url TEXT,
                source_title TEXT,
                provider TEXT,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                saved_at TEXT NOT NULL
            );
            INSERT INTO scores_new ({columns})
            SELECT {columns} FROM scores;
            DROP TABLE scores;
            ALTER TABLE scores_new RENAME TO scores;
            """
        )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "query": row["query"],
            "artist": row["artist"],
            "song_title": row["song_title"],
            "score_type": row["score_type"],
            "memo": row["memo"],
            "media_kind": row["media_kind"],
            "mime_type": row["mime_type"],
            "extension": row["extension"],
            "storage_path": row["storage_path"],
            "storage_filename": row["storage_filename"],
            "source_url": row["source_url"],
            "source_page_url": row["source_page_url"],
            "source_title": row["source_title"],
            "provider": row["provider"],
            "file_size": row["file_size"],
            "sha256": row["sha256"],
            "saved_at": row["saved_at"],
        }
