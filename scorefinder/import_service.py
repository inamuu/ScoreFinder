from __future__ import annotations

import json
import re
from html import escape, unescape
from urllib.parse import urlparse

import httpx

from .utils import is_remote_url


HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    )
}

UFRET_ARRAY_RE = re.compile(r"var\s+ufret_chord_datas\s*=\s*(\[[\s\S]*?\]);")
UFRET_DATA_ATTR_RE = re.compile(r'data-song-name="([^"]+)".*?data-artist-name="([^"]+)"', re.S)
UFRET_META_VAR_RE = re.compile(r"var\s+(lyrics|music)\s*=\s*'([^']*)';")


class ScoreImportService:
    def __init__(self) -> None:
        self.timeout = 20.0

    def import_url(self, url: str) -> dict[str, object]:
        if not is_remote_url(url):
            raise ValueError("URL が不正です")

        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host in {"ufret.jp", "www.ufret.jp"}:
            return self._import_ufret(url)

        raise ValueError("現在は U-FRET の URL 取り込みのみ対応しています")

    def _import_ufret(self, url: str) -> dict[str, object]:
        with httpx.Client(
            headers=HTTP_HEADERS,
            follow_redirects=True,
            timeout=self.timeout,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
            final_url = str(response.url)

        song_title, artist = self._extract_title_artist(html)
        lyricist, composer = self._extract_creators(html)
        lines = self._extract_lines(html)
        raw_text = "\n".join(lines)

        payload = {
            "provider": "U-FRET",
            "media_kind": "html",
            "source_url": final_url,
            "source_page_url": final_url,
            "source_title": f"{song_title} / {artist}",
            "song_title": song_title,
            "artist": artist,
            "score_type": "コード譜",
            "lyricist": lyricist,
            "composer": composer,
            "line_count": len(lines),
            "raw_text": raw_text,
        }
        payload["preview_html"] = self.build_preview_html(payload)
        return payload

    @staticmethod
    def _extract_title_artist(html: str) -> tuple[str, str]:
        match = UFRET_DATA_ATTR_RE.search(html)
        if match:
            song_title = unescape(match.group(1)).strip()
            artist = unescape(match.group(2)).strip()
            return song_title, artist

        title_match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        if not title_match:
            raise ValueError("曲名とアーティスト名を抽出できませんでした")

        title_text = unescape(title_match.group(1))
        song_title = title_text.split("/")[0].strip()
        artist = title_text.split("/")[1].split("ギターコード")[0].strip() if "/" in title_text else "Unknown"
        return song_title or "Unknown", artist or "Unknown"

    @staticmethod
    def _extract_creators(html: str) -> tuple[str | None, str | None]:
        values: dict[str, str] = {}
        for kind, value in UFRET_META_VAR_RE.findall(html):
            values[kind] = unescape(value).strip()
        lyricist = values.get("lyrics") or None
        composer = values.get("music") or None
        return lyricist, composer

    @staticmethod
    def _extract_lines(html: str) -> list[str]:
        match = UFRET_ARRAY_RE.search(html)
        if not match:
            raise ValueError("コード譜データを抽出できませんでした")

        raw_lines = json.loads(match.group(1))
        lines: list[str] = []
        for line in raw_lines:
            cleaned = line.replace("\ufeff", "").rstrip("\r\n")
            lines.append(cleaned)
        return lines

    @staticmethod
    def build_preview_html(payload: dict[str, object]) -> str:
        title = escape(str(payload["song_title"]))
        artist = escape(str(payload["artist"]))
        source_url = escape(str(payload["source_url"]))
        score_type = escape(str(payload["score_type"]))
        provider = escape(str(payload["provider"]))
        lyricist = escape(str(payload.get("lyricist") or "-"))
        composer = escape(str(payload.get("composer") or "-"))
        raw_text = escape(str(payload["raw_text"]))

        return f"""<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} | {artist}</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #fbf7ee;
        --ink: #2f2418;
        --muted: #6a543d;
        --line: rgba(95, 45, 18, 0.18);
        --accent: #8f4a20;
      }}

      body {{
        margin: 0;
        padding: 24px;
        background: linear-gradient(180deg, #fffdf8, var(--bg));
        color: var(--ink);
        font-family: "Hiragino Sans", "Yu Gothic", sans-serif;
      }}

      .sheet {{
        max-width: 900px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 28px;
      }}

      h1 {{
        margin: 0 0 6px;
        font-size: 2rem;
      }}

      .meta {{
        margin: 0;
        color: var(--muted);
        line-height: 1.7;
      }}

      .source {{
        display: inline-block;
        margin-top: 12px;
        color: var(--accent);
        text-decoration: none;
        font-weight: 700;
      }}

      pre {{
        margin: 24px 0 0;
        padding: 20px;
        border-radius: 18px;
        background: #fffaf1;
        border: 1px solid var(--line);
        color: var(--ink);
        font: 400 15px/1.85 "SFMono-Regular", "Menlo", monospace;
        white-space: pre-wrap;
        word-break: break-word;
      }}
    </style>
  </head>
  <body>
    <article class="sheet">
      <h1>{title}</h1>
      <p class="meta">アーティスト: {artist}</p>
      <p class="meta">譜面種別: {score_type} / 取り込み元: {provider}</p>
      <p class="meta">作詞: {lyricist} / 作曲: {composer}</p>
      <a class="source" href="{source_url}" target="_blank" rel="noreferrer">元ページを開く</a>
      <pre>{raw_text}</pre>
    </article>
  </body>
</html>
"""
