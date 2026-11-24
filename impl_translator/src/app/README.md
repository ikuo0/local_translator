# impl_translator Flask UI

Flask ベースのメインアプリケーション。SR99xx 機能の UI を一元管理します。

## ファイル構成

```
impl_translator/src/
├── app/
│   ├── app.py              # メイン Flask アプリケーション
│   ├── html/               # ルートの静的ファイル（目次など）
│   │   └── index.html      # / アクセス時に表示
│   └── __init__.py
│
└── features/
    ├── SR1001/
    │   ├── app/            # SR1001 API ルート
    │   ├── html/           # SR1001 静的ファイル（HTML/CSS/JS）
    │   │   └── index.html
    │   ├── batch/          # CLI コマンド（本機能は不要）
    │   └── spec.md
    │
    └── common/             # 共有モジュール
```

## ルーティング構造

### 明示的なルーティング

| URL | 対象ファイル | 説明 |
|-----|------------|------|
| `/` | `impl_translator/src/app/html/index.html` | ルート目次（SR1001等へのリンク）|
| `/{filename}` | `impl_translator/src/app/html/{filename}` | ルートの静的ファイル |
| `/sr1001/` | `impl_translator/src/features/SR1001/html/index.html` | SR1001 ジョブ進捗監視画面 |
| `/sr1001/{filename}` | `impl_translator/src/features/SR1001/html/{filename}` | SR1001 の静的ファイル |
| `/sr1001/?id={job_id}` | SR1001 ダッシュボード（auto-load） | ジョブ ID で自動読み込み |

### API エンドポイント

```
GET /sr1001/api/job/<job_id>          # ジョブ状態取得（JSON）
GET /sr1001/api/job/<job_id>/pages    # ページ詳細取得（JSON）
```

## 起動方法

### 開発モード（推奨）

#### デフォルトディレクトリ
```bash
cd /workspace
PYTHONPATH=/workspace python -m flask --app impl_translator.src.app.app run
```

#### カスタムジョブディレクトリを指定
```bash
cd /workspace
PYTHONPATH=/workspace IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
python -m flask --app impl_translator.src.app.app run
```

**アクセス先：**
- **目次**: `http://localhost:5000/`
- **SR1001**: `http://localhost:5000/sr1001/`
- **SR1001（auto-load）**: `http://localhost:5000/sr1001/?id={job_id}`

### 本番モード（Gunicorn）

```bash
# Gunicorn インストール
pip install gunicorn

# デフォルトディレクトリ
cd /workspace
PYTHONPATH=/workspace gunicorn -w 4 -b 0.0.0.0:5000 "impl_translator.src.app:create_app()"

# カスタムジョブディレクトリを指定
cd /workspace
IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
PYTHONPATH=/workspace gunicorn -w 4 -b 0.0.0.0:5000 "impl_translator.src.app:create_app()"
```

## 環境変数

### IMPL_TRANSLATOR_WORKING_DIR

ジョブ状態ファイルが保存されているディレクトリを指定します。

**デフォルト値：** `output/job`

**使用例：**
```bash
# _data/odbpp_translatol プロジェクトのジョブを監視
IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
PYTHONPATH=/workspace python -m flask --app impl_translator.src.app.app run

# 別のプロジェクト
IMPL_TRANSLATOR_WORKING_DIR="/path/to/another/job/dir" \
PYTHONPATH=/workspace python -m flask --app impl_translator.src.app.app run
```

## 使用例

### 1. UI を起動して目次を表示

```bash
PYTHONPATH=/workspace IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
python -m flask --app impl_translator.src.app.app run
```

ブラウザで `http://localhost:5000/` を開く

### 2. 特定のジョブの進捗を監視

ジョブ ID: `31b4adf2021a427598ca3f90ede26a1b`

```bash
# サーバー起動
PYTHONPATH=/workspace IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
python -m flask --app impl_translator.src.app.app run
```

ブラウザで以下にアクセス：
```
http://localhost:5000/sr1001/?id=31b4adf2021a427598ca3f90ede26a1b
```

ページが自動的にジョブ ID を読み込み、進捗を表示します。

### 3. API で JSON データを取得

```bash
# ジョブ状態
curl http://localhost:5000/sr1001/api/job/31b4adf2021a427598ca3f90ede26a1b

# ページ詳細
curl http://localhost:5000/sr1001/api/job/31b4adf2021a427598ca3f90ede26a1b/pages
```

## 新しい SR99xx UI を追加

1. `impl_translator/src/features/SR99xx/html/` ディレクトリを作成
2. `index.html` と他の HTML/CSS/JS ファイルを配置
3. `impl_translator/src/features/SR99xx/app/__init__.py` で API ルートを定義（必要な場合）
4. `app.py` の `create_app()` に以下を追加（必要な場合）：
   ```python
   from impl_translator.src.features.SR99xx.app import bp as sr99xx_bp
   app.register_blueprint(sr99xx_bp)
   ```

追加後、`/sr99xx/` でアクセス可能になります。

## セキュリティ

- `send_from_directory()` は自動的にパストラバーサル攻撃を防止
- 指定された html/ ディレクトリのみ提供
- 親ディレクトリへのアクセスを防止

## 拡張

### WebSocket でリアルタイム更新

```python
# app.py に追加
from flask_socketio import SocketIO
socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect(data):
    # クライアント接続処理
    pass
```

### CORS 対応

```python
# app.py に追加
from flask_cors import CORS
CORS(app)
```

## トラブルシューティング

### "Job not found" エラーが表示される

- ジョブ ID が正確であることを確認
- ジョブディレクトリが存在することを確認
- `IMPL_TRANSLATOR_WORKING_DIR` 環境変数が正しく設定されていることを確認

```bash
# 確認方法
ls -la _data/odbpp_translatol/output/job/{job_id}/job.yaml
```

### API が 404 を返す

- URL が正確であることを確認
- ジョブ ID の形式が正しいことを確認（32文字の16進数）

```bash
# 有効なジョブ ID の例
31b4adf2021a427598ca3f90ede26a1b
```


