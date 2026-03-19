from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scorefinder.database import ScoreRepository
from scorefinder.models import StoredFile
from scorefinder.schemas import SaveScoreRequest


class ScoreRepositoryTests(unittest.TestCase):
    def test_insert_and_filter_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "scores.sqlite3"
            repo = ScoreRepository(db_path)
            repo.initialize()

            request = SaveScoreRequest(
                query="スピッツ チェリー コード譜",
                artist="スピッツ",
                song_title="チェリー",
                score_type="コード譜",
                media_kind="pdf",
                source_url="https://example.com/cherry.pdf",
                source_page_url="https://example.com/cherry",
                source_title="チェリー PDF",
                provider="Test",
                memo="原曲キー",
            )
            stored = StoredFile(
                path=Path(tmp_dir) / "cherry.pdf",
                filename="cherry.pdf",
                mime_type="application/pdf",
                extension="pdf",
                media_kind="pdf",
                file_size=12345,
                sha256="abc123",
            )

            repo.insert_score(request, stored)
            results = repo.search_scores(artist="スピッツ", media_kind="pdf")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["song_title"], "チェリー")
            self.assertEqual(results[0]["memo"], "原曲キー")


if __name__ == "__main__":
    unittest.main()
