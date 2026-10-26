# ランナーログ 開発メモ

ガンプラの積み・欲しい・製作中・完成と作業記録を管理する単一ファイルのWebアプリ（`index.html`）。Claude Code と Codex の両方がこのメモを読む。

## 構成
- 画面とロジックは `index.html` 1ファイル（外部依存はGoogle Fontsと、バーコード読み取り時のZXingのみ）。
- 保存は `db.collection("kits"|"logs")` と `assets`（写真）を通す。配布版ではIndexedDB製の代用品（`makeCol` / `photoStore`）が入っている。
- 本人用はclaude.aiのArtifact（データはclaude.ai側のdbに同期）。同じ画面コードで、保存部分だけ差し替えて使う。本人用のURLは公開しない。

## 方針
- 本人用が本命、配布版は機能を絞った版。配布版で作った機能は本人用に逆輸入してよい。
- 画面側に足した機能は、保存部分に依存させない（`db` / `assets` のAPIだけを使う）。
- 配布版に本人のデータを入れない。

## データ
- kits: name, model(型式), jan, grade, status(wish/stock/building/done), price, shop, bought, started, finished, memo, recipe, review, photos[id], folder, next, theme, want, notWant, refs
- logs: kitId, date, type(memo/work/try/decide/done。無い旧ログはwork), memo, step, minutes, photos[id], ref, idea(''/cand/adopt/skip), created
- 新規キットは保存・記録・写真の最初の操作までDBに作らない（下書きは `draft` / `"__new"`）。

## 作業ルール
- 作業ごとにブランチを切り、mainへのマージはオーナーが確認してから。
- 変更後は `<script>` の構文確認（例: `node -e` で `new Function`）をしてから push する。
- 同時に触る場合は、先に `git pull` する。
