# SR1001 ジョブ進捗監視 - 使用方法

## 概要

SR1001 は、PDF 翻訳ジョブの進捗をリアルタイムで監視する Web UI です。
Flask ベースのダッシュボードで、ジョブの進行状況をページごとに確認できます。

## 起動方法

### 1. 環境変数を設定

```bash
export PYTHONPATH=/workspace
export IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job"
```

### 2. Flask サーバーを起動

```bash
python -m flask --app impl_translator.src.app.app run
```

サーバーが起動すると：
```
 * Running on http://127.0.0.1:5000
```

## アクセス方法

### パターン 1: 目次から選択

1. ブラウザで `http://localhost:5000/` を開く
2. 目次ページが表示される
3. 「SR1001 - ジョブ進捗監視」をクリック
4. ジョブ ID を入力して検索

### パターン 2: 直接 URL でアクセス（推奨）

ジョブ ID: `31b4adf2021a427598ca3f90ede26a1b`

```
http://localhost:5000/sr1001/?id=31b4adf2021a427598ca3f90ede26a1b
```

ページが自動的にジョブ ID を読み込み、進捗を表示します。

### パターン 3: API で JSON を取得

```bash
# ジョブ全体の状態
curl http://localhost:5000/sr1001/api/job/31b4adf2021a427598ca3f90ede26a1b

# 応答例
{
  "job_id": "31b4adf2021a427598ca3f90ede26a1b",
  "status": "running",
  "total_pages": 534,
  "completed": 4,
  "failed": 0,
  "interrupted": 0,
  "running": 1,
  "progress_percent": 0.7,
  "created_at": "2026-11-24T05:52:11.139011+00:00",
  "updated_at": "2026-11-24T06:16:04.513416+00:00"
}
```

ページ詳細：

```bash
curl http://localhost:5000/sr1001/api/job/31b4adf2021a427598ca3f90ede26a1b/pages
```

## UI の説明

### ダッシュボード画面

**上部入力エリア**
- ジョブ ID 入力フィールド
- 「検索」ボタン（Enter キーでも実行可）

**進捗表示エリア**
- **ジョブ ID**: 監視中のジョブ識別子
- **ステータス**: 実行中 / 完了 / 中断など
- **総ページ数**: PDF のページ総数
- **完了ページ数**: 翻訳が完了したページ
- **失敗ページ数**: 翻訳に失敗したページ
- **実行中ページ数**: 現在処理中のページ
- **経過時間**: ジョブ開始からの経過時間

**進捗バー**
- 完了率を視覚的に表示（0-100%）
- 色付きバーで現在の進捗を確認

**ページ一覧**
- 各ページの状態を表示
- 完了/実行中/失敗/中断の色分け表示

## 自動更新機能

UI は 5 秒ごとに自動で API を呼び出し、進捗を更新します。
ページを閉じるまで、継続的にジョブの進捗を監視できます。

## トラブルシューティング

### "Job not found" エラー

**原因**: ジョブ ID が見つからない

**確認方法**:
```bash
# ジョブディレクトリが存在するか確認
ls -la _data/odbpp_translatol/output/job/31b4adf2021a427598ca3f90ede26a1b/

# job.yaml が存在するか確認
cat _data/odbpp_translatol/output/job/31b4adf2021a427598ca3f90ede26a1b/job.yaml
```

### API が 404 を返す

**原因**: ジョブ ID の形式が正しくない

**有効な形式**: 32 文字の 16 進数
```
31b4adf2021a427598ca3f90ede26a1b  ✓ OK
```

## 動作例

### ジョブが実行中の場合

```json
{
  "job_id": "31b4adf2021a427598ca3f90ede26a1b",
  "status": "running",
  "total_pages": 534,
  "completed": 100,
  "failed": 2,
  "interrupted": 0,
  "running": 1,
  "progress_percent": 18.9,
  "elapsed_seconds": 3600
}
```

UI では：
- 進捗バーが 18.9% を表示
- 「完了: 100 ページ」と表示
- 「失敗: 2 ページ」と表示
- 「実行中ページ数: 1」と表示

### ジョブが完了した場合

```json
{
  "job_id": "31b4adf2021a427598ca3f90ede26a1b",
  "status": "completed",
  "total_pages": 534,
  "completed": 534,
  "failed": 0,
  "interrupted": 0,
  "running": 0,
  "progress_percent": 100.0
}
```

UI では：
- 進捗バーが 100% を表示
- 「完了: 534 ページ」と表示
- ステータスが「completed」と表示

## 本番環境での起動

### Gunicorn を使用した本番環境起動

```bash
# Gunicorn インストール
pip install gunicorn

# 起動
PYTHONPATH=/workspace \
IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
gunicorn -w 4 -b 0.0.0.0:5000 "impl_translator.src.app:create_app()"
```

### Nginx リバースプロキシ設定例

```nginx
server {
    listen 80;
    server_name translator.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 応用例

### Shell スクリプトでジョブ監視

```bash
#!/bin/bash

JOB_ID="31b4adf2021a427598ca3f90ede26a1b"
API_URL="http://localhost:5000/sr1001/api/job/$JOB_ID"

while true; do
    RESPONSE=$(curl -s "$API_URL")
    PROGRESS=$(echo "$RESPONSE" | grep -o '"progress_percent": [0-9.]*' | awk '{print $2}')
    STATUS=$(echo "$RESPONSE" | grep -o '"status": "[^"]*' | cut -d'"' -f4)
    
    echo "Status: $STATUS | Progress: ${PROGRESS}%"
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "interrupted" ]; then
        echo "ジョブが終了しました"
        break
    fi
    
    sleep 10
done
```

## 参考情報

- **Flask UI**: `impl_translator/src/app/`
- **SR1001 仕様**: `impl_translator/src/features/SR1001/spec.md`
- **ジョブ管理**: `impl_translator/src/libs/job/`
