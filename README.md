# ScoreFinder

ScoreFinder は、U-FRET など対応サイトの楽譜 URL を 1 件ずつ取り込み、NAS など任意の保存先に整理保存し、保存済みメタデータをあとから検索できるローカルアプリです。

## できること

- U-FRET の楽譜 URL を指定してコード譜を取り込み
- 取り込んだコード譜をローカル HTML としてプレビュー・保存
- 保存時に `アーティスト名 / 楽曲名 / 譜面種別 / メモ` を付与
- 保存済みの楽譜を `自由検索 / アーティスト名 / 楽曲名 / 譜面種別 / ファイル種別 / 保存日` で再検索
- 保存先は NAS のマウントパスなど任意の絶対パスを指定
- 大量クロールを避け、URL ベースの明示的な取り込みに限定

## 前提

- Python 3.11 以上
- NAS を使う場合は事前に OS 側でマウント済みであること

## セットアップ

```bash
uv sync
```

## 起動

```bash
uv run scorefinder
```

または:

```bash
uv run uvicorn scorefinder.app:app --reload
```

起動後に [http://127.0.0.1:8000](http://127.0.0.1:8000) を開いてください。

## 使い方

1. U-FRET の曲ページ URL を入力して取り込みます
2. 曲名・アーティスト名・譜面種別を確認または修正します
3. NAS 保存先へ HTML とメタデータを保存します
4. 保存済み検索であとからフィルタ検索します

## 補足

- 保存先は初回起動時に `~/.scorefinder/storage` が既定値になります。
- 設定ファイル本体は、設定した保存先直下の `scorefinder.config.json` に保存されます。
- SQLite データベースは、設定した保存先直下の `scorefinder.sqlite3` に保存されます。
- ローカルには、前回の保存先だけを覚える bootstrap 情報 `~/.scorefinder/bootstrap.json` を置きます。
- 既存の `~/.scorefinder/config.json` は bootstrap 元データとして扱い、必要に応じて NAS 側の設定へ移行します。
- 既存のローカル DB が `~/.scorefinder/scorefinder.sqlite3` にある場合は、初回アクセス時に保存先配下へ移動します。
- 現在の URL 取り込みは U-FRET の曲ページに対応しています。
- 権利処理が必要な楽譜は、利用許諾のあるものだけ保存してください。
