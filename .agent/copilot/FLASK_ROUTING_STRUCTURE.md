# Flask UI ルーティング構造

## 概要

impl_translator の Flask UI は以下の明示的なルーティング構造を採用しています。

## ルーティング一覧

### ルート（/）
- **URL**: `/`
- **ファイル**: `impl_translator/src/app/html/index.html`
- **説明**: 目次ページ。SR1001 などの機能へのリンクを表示

### ルート直下の静的ファイル
- **URL**: `/{filename}`
- **ファイル**: `impl_translator/src/app/html/{filename}`
- **説明**: ルートの静的ファイル（CSS、JS、画像など）

### SR1001 インデックス
- **URL**: `/sr1001/`
- **ファイル**: `impl_translator/src/features/SR1001/html/index.html`
- **説明**: ジョブ進捗監視ダッシュボード

### SR1001 静的ファイル
- **URL**: `/sr1001/{filename}`
- **ファイル**: `impl_translator/src/features/SR1001/html/{filename}`
- **説明**: SR1001 の CSS、JS、画像など

### SR1001 API エンドポイント
- **URL**: `/sr1001/api/job/{job_id}`
- **メソッド**: GET
- **説明**: 指定ジョブの状態を取得

- **URL**: `/sr1001/api/job/{job_id}/pages`
- **メソッド**: GET
- **説明**: ジョブのページ詳細を取得

## ファイル構成

```
impl_translator/src/
├── app/
│   ├── app.py              # メイン Flask アプリケーション
│   ├── html/               # ルート (/) の静的ファイル
│   │   └── index.html      # ルート目次
│   └── __init__.py
│
└── features/
    ├── SR1001/
    │   ├── app/
    │   │   └── __init__.py # API エンドポイント定義
    │   ├── html/           # SR1001 (/sr1001/) の静的ファイル
    │   │   └── index.html  # SR1001 ダッシュボード
    │   ├── batch/
    │   └── spec.md
    │
    └── common/
        └── __init__.py     # 共有データ構造
```

## app.py の実装パターン

Flask アプリは以下の順序でルートを登録：

1. **BP（ブループリント）登録** - API エンドポイント（高優先度）
2. **SR1001 ルート** - `/sr1001/` と `/sr1001/<path:filename>`
3. **ルート ルート** - `/` と `/<path:filename>`

```python
def create_app() -> Flask:
    app = Flask(__name__)
    
    # API ルート（先に登録 - 優先度が高い）
    from impl_translator.src.features.SR1001.app import bp as sr1001_bp
    app.register_blueprint(sr1001_bp)
    
    # SR1001 HTML ルート
    @app.route("/sr1001/")
    @app.route("/sr1001/<path:filename>")
    
    # ルート HTML ルート（後に登録 - ワイルドカード対応）
    @app.route("/")
    @app.route("/<path:filename>")
    
    return app
```

## 新規 SR99xx 機能を追加する場合

1. **ディレクトリ作成**
   ```
   impl_translator/src/features/SR99xx/
   ├── app/
   │   └── __init__.py     # API ルート定義（必要に応じて）
   ├── html/
   │   └── index.html      # UI
   └── batch/
   ```

2. **app.py に登録**
   ```python
   from impl_translator.src.features.SR99xx.app import bp as sr99xx_bp
   app.register_blueprint(sr99xx_bp)
   ```

3. **ルートを追加**
   ```python
   sr99xx_html_path = Path(__file__).parent.parent / "features" / "SR99xx" / "html"
   
   @app.route("/sr99xx/")
   def sr99xx_index():
       return send_from_directory(sr99xx_html_path, "index.html")
   
   @app.route("/sr99xx/<path:filename>")
   def serve_sr99xx_static(filename: str):
       try:
           return send_from_directory(sr99xx_html_path, filename)
       except Exception:
           return {"error": f"File not found: {filename}"}, 404
   ```

## セキュリティ考慮事項

- **send_from_directory()**: 自動的にパストラバーサル攻撃を防止
- **html/ ディレクトリのみ**: 指定されたディレクトリ外のファイルにアクセス不可
- **エラーハンドリング**: ファイルが見つからない場合は 404 を返す

## 起動コマンド

```bash
# 開発モード
PYTHONPATH=/workspace IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
python -m flask --app impl_translator.src.app.app run

# 本番モード（Gunicorn）
PYTHONPATH=/workspace IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
gunicorn -w 4 -b 0.0.0.0:5000 "impl_translator.src.app:create_app()"
```

## アクセス先

- **ルート目次**: http://localhost:5000/
- **SR1001 ダッシュボード**: http://localhost:5000/sr1001/
- **API**: http://localhost:5000/sr1001/api/job/{job_id}
