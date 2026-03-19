from __future__ import annotations

import unittest

from scorefinder.utils import (
    guess_extension,
    looks_like_sample,
    normalize_search_query,
    sanitize_component,
)


class UtilsTests(unittest.TestCase):
    def test_sample_detection(self) -> None:
        self.assertTrue(looks_like_sample("free sample score", None))
        self.assertTrue(looks_like_sample("公式サンプル", None))
        self.assertFalse(looks_like_sample("complete score", None))

    def test_query_normalization(self) -> None:
        self.assertEqual(normalize_search_query("スピッツ チェリー"), "スピッツ チェリー 楽譜")
        self.assertEqual(normalize_search_query("スピッツ チェリー コード譜"), "スピッツ チェリー コード譜")

    def test_sanitize_component(self) -> None:
        self.assertEqual(sanitize_component(" BUMP OF CHICKEN / 天体観測 "), "BUMP_OF_CHICKEN_天体観測")
        self.assertEqual(sanitize_component(" スピッツ / チェリー "), "スピッツ_チェリー")

    def test_guess_extension(self) -> None:
        self.assertEqual(guess_extension("https://example.com/score.pdf", None, "pdf"), "pdf")
        self.assertEqual(guess_extension("https://example.com/download", "image/png", "image"), "png")


if __name__ == "__main__":
    unittest.main()
