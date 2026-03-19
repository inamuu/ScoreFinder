from __future__ import annotations

from typing import Any

import httpx
from ddgs import DDGS

from .utils import is_remote_url, looks_like_sample, normalize_search_query


HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    )
}


class RemoteSearchService:
    def __init__(self) -> None:
        self.timeout = 10.0

    def search(self, query: str, limit: int = 18) -> dict[str, Any]:
        prepared_query = normalize_search_query(query)
        warnings: list[str] = []
        image_limit = max(limit - max(limit // 3, 4), 1)
        pdf_limit = max(limit - image_limit, 1)

        try:
            image_results = self._search_images(prepared_query, limit=max(image_limit, 6))
        except Exception as error:  # pragma: no cover - network dependent path
            warnings.append(f"画像検索で一部候補を取得できませんでした: {error}")
            image_results = []

        try:
            pdf_results = self._search_pdfs(prepared_query, limit=max(pdf_limit, 4))
        except Exception as error:  # pragma: no cover - network dependent path
            warnings.append(f"PDF 検索で一部候補を取得できませんでした: {error}")
            pdf_results = []

        return {
            "query": query,
            "prepared_query": prepared_query,
            "results": (image_results[:image_limit] + pdf_results[:pdf_limit])[:limit],
            "warnings": warnings,
        }

    def _search_images(self, query: str, limit: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        ddgs = DDGS(timeout=self.timeout)
        raw_results = ddgs.images(
            query=query,
            region="wt-wt",
            safesearch="off",
            max_results=max(limit * 2, 12),
            backend="duckduckgo",
        )

        for item in raw_results:
            if looks_like_sample(item.get("title"), item.get("image"), item.get("url")):
                continue

            image_url = item.get("image")
            if not image_url or not is_remote_url(image_url):
                continue

            results.append(
                {
                    "media_kind": "image",
                    "title": item.get("title") or "Untitled image",
                    "source_url": image_url,
                    "source_page_url": item.get("url"),
                    "thumbnail_url": item.get("thumbnail") or image_url,
                    "provider": item.get("source") or "DuckDuckGo",
                    "width": item.get("width"),
                    "height": item.get("height"),
                }
            )
            if len(results) >= limit:
                break

        return results

    def _search_pdfs(self, query: str, limit: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        ddgs = DDGS(timeout=self.timeout)
        raw_results = ddgs.text(
            query=f"{query} filetype:pdf",
            region="wt-wt",
            safesearch="off",
            max_results=max(limit * 4, 12),
            backend="auto",
        )

        for item in raw_results:
            href = item.get("href")
            if not href or not is_remote_url(href):
                continue
            if looks_like_sample(item.get("title"), href, item.get("body")):
                continue

            resolved_url = self._resolve_pdf_url(href)
            if resolved_url is None:
                continue

            results.append(
                {
                    "media_kind": "pdf",
                    "title": item.get("title") or "Untitled PDF",
                    "source_url": resolved_url,
                    "source_page_url": href,
                    "thumbnail_url": None,
                    "provider": "DuckDuckGo",
                    "width": None,
                    "height": None,
                }
            )
            if len(results) >= limit:
                break

        return results

    def _resolve_pdf_url(self, url: str) -> str | None:
        lowered = url.lower()
        if lowered.endswith(".pdf") or ".pdf?" in lowered:
            return url

        with httpx.Client(
            headers=HTTP_HEADERS,
            follow_redirects=True,
            timeout=self.timeout,
        ) as client:
            try:
                head_response = client.head(url)
                content_type = head_response.headers.get("content-type", "").split(";")[0].lower()
                final_url = str(head_response.url)
                if content_type == "application/pdf" or final_url.lower().endswith(".pdf"):
                    return final_url
            except httpx.HTTPError:
                pass

            try:
                get_response = client.get(url, headers={"Range": "bytes=0-1023"})
                content_type = get_response.headers.get("content-type", "").split(";")[0].lower()
                final_url = str(get_response.url)
                if content_type == "application/pdf" or final_url.lower().endswith(".pdf"):
                    return final_url
            except httpx.HTTPError:
                return None

        return None
