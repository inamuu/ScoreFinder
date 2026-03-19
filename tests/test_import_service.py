from __future__ import annotations

import unittest

from scorefinder.import_service import ScoreImportService


UFRET_SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="ja">
  <head>
    <title>卒業写真 / 荒井由実(松任谷由実)  ギターコード - U-FRET(U-フレット)</title>
  </head>
  <body>
    <button data-song-name="卒業写真" data-artist-name="荒井由実(松任谷由実)"></button>
    <script>
      var lyrics      = '荒井由実';
      var music       = '荒井由実';
      var ufret_chord_datas = ["\\ufeff[Dm7] 卒[G7]業写真\\r", "", "やさし[Dm7]い目[G7]をして[Cmaj7]る\\r"];
    </script>
  </body>
</html>
"""


class ImportServiceTests(unittest.TestCase):
    def test_extracts_ufret_metadata_and_lines(self) -> None:
        service = ScoreImportService()
        song_title, artist = service._extract_title_artist(UFRET_SAMPLE_HTML)
        lyricist, composer = service._extract_creators(UFRET_SAMPLE_HTML)
        lines = service._extract_lines(UFRET_SAMPLE_HTML)

        self.assertEqual(song_title, "卒業写真")
        self.assertEqual(artist, "荒井由実(松任谷由実)")
        self.assertEqual(lyricist, "荒井由実")
        self.assertEqual(composer, "荒井由実")
        self.assertEqual(lines[0], "[Dm7] 卒[G7]業写真")
        self.assertEqual(lines[2], "やさし[Dm7]い目[G7]をして[Cmaj7]る")

    def test_build_preview_html_contains_source_metadata(self) -> None:
        service = ScoreImportService()
        html = service.build_preview_html(
            {
                "song_title": "卒業写真",
                "artist": "荒井由実(松任谷由実)",
                "score_type": "コード譜",
                "provider": "U-FRET",
                "lyricist": "荒井由実",
                "composer": "荒井由実",
                "source_url": "https://www.ufret.jp/song.php?data=963",
                "raw_text": "[Dm7] 卒[G7]業写真",
            }
        )

        self.assertIn("卒業写真", html)
        self.assertIn("U-FRET", html)
        self.assertIn("https://www.ufret.jp/song.php?data=963", html)


if __name__ == "__main__":
    unittest.main()
