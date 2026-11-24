# SR1001: Job Progress Monitoring UI

## 概要

SR1000（PDF翻訳バッチ処理）の進捗をリアルタイムで確認できるWeb UIを提供します。

## 機能

- **進捗ダッシュボード**
  - ジョブID指定で進捗確認
  - ページ単位の完了/失敗/実行中状態表示
  - 全体進捗率（パーセンテージ）
  - 経過時間

- **ジョブ詳細情報**
  - ステータス（created/running/completed/interrupted/error）
  - ページごとの詳細情報（処理時間、文字数等）
  - ログファイルパス
  - 作成日時、最終更新日時

- **API エンドポイント**
  - `GET /sr1001/api/job/<job_id>` - ジョブ状態取得
  - `GET /sr1001/api/job/<job_id>/pages` - ページ詳細取得

## ファイル構成

```
impl_translator/src/features/SR1001/
├── app/
│   └── __init__.py          # Flask ブループリント、ルート定義
├── batch/
│   └── __init__.py          # (空) コマンド実行不要
├── spec.md                  # このファイル
└── __init__.py              # (自動生成)
```

## 実装詳細

### app/__init__.py

#### ルート

**GET /sr1001/**
- ダッシュボード HTML を返す
- Job ID を入力してモニタリング開始

**GET /sr1001/api/job/<job_id>**
- JSON でジョブ状態を返す
- 進捗率、完了/失敗ページ数等を計算

**GET /sr1001/api/job/<job_id>/pages**
- ページごとの詳細情報を返す
- ステータス、処理時間、エラー情報等

### libs との連携

- `impl_translator.src.libs.job.load()` - 状態ファイル読み込み
- `impl_translator.src.libs.job.lock()` - ジョブロック取得（読み取り専用）

## 使用例

### Web UI へアクセス

```bash
# Flask 起動
python -m flask --app impl_translator.src.features.SR1001.app run

# ブラウザで以下にアクセス
http://localhost:5000/sr1001/
```

### API で状態取得

```bash
# ジョブ全体の進捗確認
curl http://localhost:5000/sr1001/api/job/f8d70f3e98404d3c931e3994f83f3f8c

# ページ詳細確認
curl http://localhost:5000/sr1001/api/job/f8d70f3e98404d3c931e3994f83f3f8c/pages
```

## 拡張予定

- WebSocket でリアルタイム更新
- 一時停止・再開ボタン
- ログビューア
- ページ単位での再実行
