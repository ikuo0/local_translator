# impl_translator アーキテクチャポリシー

## ディレクトリ構造

```
impl_translator/src/
├── features/
│   ├── SR1000/              # 個別機能
│   │   ├── app/             # (Optional) Flask/FastAPI ルート定義
│   │   ├── batch/           # (Optional) CLI コマンド実装
│   │   └── spec.md          # 機能仕様書
│   ├── SR1001/
│   │   ├── app/             # Flask ルート
│   │   ├── batch/           # (空) コマンド実行不要
│   │   └── spec.md
│   ├── common/              # 共有モジュール
│   │   ├── __init__.py      # 共有データ構造、関数
│   │   └── spec.md          # (Optional) 仕様書
│   └── SR99xx/              # 他の機能
├── libs/
│   ├── job/                 # ジョブ状態管理（全機能で共有）
│   ├── translator/          # LLM 翻訳エンジン（全機能で共有）
│   └── spec.md              # ライブラリ仕様書
└── overview.md              # プロジェクト全体概観
```

---

## 命名規則

### フォルダ名

- **SR99xx** - 機能単位
  - SR1000: PDF英語→日本語翻訳バッチ
  - SR1001: バッチ進捗モニタリングUI
  - SR1100: フリー翻訳機能
  - SR1200: フリー問い合わせ機能

- **common** - SR99xx 間で共有するデータ・機能

- **libs** - 複数 SR99xx で使用する基盤ライブラリ
  - **job** - ジョブ状態管理
  - **translator** - LLM 翻訳エンジン
  - 他のユーティリティ

### ファイル名

- `app/` - **Web ルート定義**（Flask Blueprint）
  - `__init__.py` - ルート定義、エンドポイント実装
  - テンプレートは `impl_translator/templates/sr99xx/` に配置

- `batch/` - **CLI コマンド実装**
  - `__init__.py` または `batch.py` - コマンド機能
  - 存在しない場合は空にする

- `spec.md` - **機能仕様書**（必須）
  - 目的、API仕様、使用例、ファイル構成を記載

---

## ファイル設計

### SR99xx モジュール

```
SR99xx/
├── app/
│   └── __init__.py          # Flask Blueprint 定義
│       - @bp.route()
│       - エンドポイント実装
│       - common/libs との連携
│
├── batch/
│   └── __init__.py または batch.py
│       - argparse による CLI コマンド
│       - main() 関数 → sys.exit()
│       - (不要な場合は空)
│
├── spec.md                  # 仕様書
│       - 概要
│       - 機能一覧
│       - API エンドポイント
│       - ファイル構成
│       - 実装詳細
│       - 使用例
│
└── __init__.py              # (自動生成可)
    - 必要に応じて create_app() 等をエクスポート
```

### common モジュール

```
common/
├── __init__.py
│   - データクラス（@dataclass）
│   - 共有関数
│   - 列挙値
│   例：JobStatus, PageStatus, calculate_progress()
│
└── spec.md (Optional)
    - 共有データ構造仕様
```

### libs モジュール

```
libs/
├── job/
│   ├── __init__.py
│   │   - create(), load(), save(), lock()
│   │   - 全 SR99xx で使用
│   └── spec.md
│
├── translator/
│   ├── __init__.py
│   │   - translate_page()
│   │   - 全 SR99xx で使用
│   └── spec.md
│
└── (その他ユーティリティ)
```

---

## 連携フロー

```
SR1000 (batch)
  ↓
  libs.job (状態ファイル読み書き)
  libs.translator (LLM 翻訳実行)
  common.JobStatus (共有データ型)
  ↓
  状態ファイル: job.yaml

SR1001 (web UI)
  ↓
  libs.job (状態ファイル読み込み)
  common.calculate_progress() (進捗計算)
  common.JobStatus (データ変換)
  ↓
  API JSON 返却
```

---

## 実装ガイドライン

### 新しい SR99xx 機能を追加する場合

1. **ディレクトリ構造を作成**
   ```bash
   mkdir -p impl_translator/src/features/SR99xx/{app,batch}
   ```

2. **spec.md を先に作成**
   - 目的、機能、API エンドポイントを明記

3. **app/\_\_init\_\_.py を実装**
   - Flask Blueprint で必要なルートを定義
   - `common/` のデータ型を使用
   - `libs/` を必要に応じて利用

4. **batch/\_\_init\_\_.py を実装（不要ならスキップ）**
   - CLI コマンドが必要な場合のみ実装

5. **common/\_\_init\_\_.py を拡張**
   - 複数機能で共有するデータ型があれば追加

### libs との連携

- `libs.job` - ジョブの永続化状態管理（全機能必須）
- `libs.translator` - LLM 翻訳エンジン（翻訳機能が必要な場合）
- 新しいユーティリティが必要な場合は `libs/` 配下に追加

### common との連携

- SR99xx 間で共有するデータ型は `common/` に定義
- 機能固有の型は各 SR99xx/app/\_\_init\_\_.py に定義

---

## ベストプラクティス

✅ **やるべき事**

- `spec.md` は実装前に作成し、全体設計を明記
- 共有データはデータクラス (@dataclass) で型安全性を確保
- Flask ブループリント で重複コードを削減
- libs 層で基盤機能を共通化
- ジョブ状態は `libs.job` で一元管理

❌ **やってはいけない事**

- common/ にビジネスロジックを実装（データ構造のみ）
- SR99xx 固有の処理を libs/ に混入させる
- 状態管理を複数箇所で実装
- app/ で直接ファイルI/Oを行わない（libs.job を使用）

---

## テンプレート例

### 新機能作成スケルトン

```python
# impl_translator/src/features/SR99xx/app/__init__.py
from flask import Blueprint, jsonify
from impl_translator.src.features import common
from impl_translator.src.libs import job

bp = Blueprint("sr99xx", __name__, url_prefix="/sr99xx")

@bp.route("/api/status/<job_id>")
def get_status(job_id: str):
    """Get job status."""
    working_dir = Path("output/job")
    state = job.load(working_dir, job_id)
    
    # common.JobStatus を使用
    progress = common.calculate_progress(state["data"]["pages"])
    
    return jsonify(progress)
```

---

## 拡張例

### WebSocket でリアルタイム更新を追加する場合

1. `app/__init__.py` に Flask-SocketIO を統合
2. `common/__init__.py` に変更検知関数を追加
3. 状態変更を検知して WebSocket イベント発行

### 新しい LLM エンジンを追加する場合

1. `libs/` に新しいサブモジュール作成（例: `llm/`）
2. 既存の `translator/` と同じインターフェース定義
3. 各 SR99xx で選択可能にする

---

**このポリシーを遵守することで、機能追加の一貫性とメンテナンス性を確保します。**
