from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class ConfigUpdate(BaseModel):
    storage_root: str = Field(min_length=1)

    @field_validator("storage_root")
    @classmethod
    def validate_storage_root(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("保存先パスを入力してください")
        return normalized


class SaveScoreRequest(BaseModel):
    query: str = Field(min_length=1)
    artist: str = Field(min_length=1)
    song_title: str = Field(min_length=1)
    score_type: str = Field(min_length=1)
    media_kind: str = Field(pattern="^(image|pdf|html)$")
    source_url: str = Field(min_length=1)
    source_page_url: str | None = None
    source_title: str | None = None
    provider: str | None = None
    memo: str | None = None

    @field_validator("query", "artist", "song_title", "score_type", "source_url")
    @classmethod
    def strip_and_require_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("必須項目が空です")
        return normalized

    @field_validator("source_page_url", "source_title", "provider", "memo")
    @classmethod
    def normalize_optional_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ScoreSearchFilters(BaseModel):
    q: str | None = None
    artist: str | None = None
    song_title: str | None = None
    score_type: str | None = None
    media_kind: str | None = Field(default=None, pattern="^(image|pdf|html)$")
    saved_from: date | None = None
    saved_to: date | None = None
