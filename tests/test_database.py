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
            storage_root = Path(tmp_dir) / "storage"
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
                path=storage_root / "スピッツ" / "チェリー" / "コード譜" / "cherry.pdf",
                filename="cherry.pdf",
                mime_type="application/pdf",
                extension="pdf",
                media_kind="pdf",
                file_size=12345,
                sha256="abc123",
            )
            stored.path.parent.mkdir(parents=True, exist_ok=True)
            stored.path.write_bytes(b"pdf")

            repo.insert_score(request, stored, storage_root=str(storage_root))
            results = repo.search_scores(artist="スピッツ", media_kind="pdf")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["song_title"], "チェリー")
            self.assertEqual(results[0]["memo"], "原曲キー")
            self.assertEqual(
                results[0]["storage_path"],
                "スピッツ/チェリー/コード譜/cherry.pdf",
            )

    def test_resolve_storage_path_supports_legacy_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_root = Path(tmp_dir) / "storage"
            target_path = storage_root / "スピッツ" / "チェリー" / "コード譜" / "cherry.pdf"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(b"pdf")

            score = {
                "artist": "スピッツ",
                "song_title": "チェリー",
                "score_type": "コード譜",
                "storage_filename": "cherry.pdf",
                "storage_path": "/Volumes/personal_folder/04_音楽/40_Scores/スピッツ/チェリー/コード譜/cherry.pdf",
            }

            resolved = ScoreRepository.resolve_storage_path(score, str(storage_root))
            self.assertEqual(resolved, target_path.resolve())


if __name__ == "__main__":
    unittest.main()
