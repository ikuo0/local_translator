# local_translator
一括翻訳プロジェクト

# Qwen3 8Bのセットアップ

プロジェクトのルートで以下を実行すると、Ollamaを起動し、Qwen3 8Bを取得して翻訳テストを行います。
** 以下のコマンドは WSL 環境で実行する、本プロジェクトのdevcontainer環境からは実行しない **

```bash
bash setup/setup_qwen3.sh
```

モデルはOllamaの公式ライブラリから取得され、Dockerの `ollama_data` ボリュームに保存されます。

# SR1000: PDF to Japanese Translation Pipeline

SR1000 は以下の 6 つの libs モジュールを統合した、PDF から日本語への自動翻訳パイプラインです。

| ステップ | モジュール | 役割 |
|---------|-----------|------|
| **SF001** | docling_converter | PDF → 1ページごと HTML |
| **SF002** | html_preproc | HTML → スタイルタグ削除 + ID付与 |
| **SF003-1** | html_text_extractor | HTML → タグ単位テキスト抽出 |
| **SF003-2** | batch_splitter | テキスト → 1500文字バッチ化 |
| **SF003-3** | translation_formatter | バッチ → Ollama で翻訳 |
| **SF004** | translation_restorer | 翻訳 → HTML 復元 |

## ⭐ 新版: SR1000 libs 統合版（推奨）

libs 統合版は、タグ単位での正確な翻訳と改行処理を実現し、より高精度な結果が期待できます。

**基本コマンド:**
```bash
python -m impl_translator.src.features.SR1000.sr1000_main \
  --input-pdf input.pdf \
  --working-dir ./work \
  --log-file ./work/log.txt
```

**全オプション:**
```bash
python -m impl_translator.src.features.SR1000.sr1000_main \
  --input-pdf input.pdf \
  --working-dir ./work \
  --log-file ./work/log.txt \
  --ollama-host http://localhost:11434 \
  --ollama-model qwen3:8b \
  --temperature 0.3 \
  --resume
```

**オプション説明:**
- `--input-pdf` (必須): 入力 PDF ファイルパス
- `--working-dir` (必須): 中間ファイルと状態を保存するディレクトリ
- `--log-file` (必須): ログファイルパス
- `--ollama-host`: Ollama のホスト URL（デフォルト: http://localhost:11434）
- `--ollama-model`: 使用するモデル（デフォルト: qwen3:8b）
- `--temperature`: 翻訳の創意性（デフォルト: 0.3）
- `--resume`: 前回の進捗から再開

## 進捗管理

各ページの処理状態は `working_dir/states/page_XXXXXX.json` に保存されます。

```json
{
  "page_id": "page_000001",
  "status": "completed",
  "steps": {
    "sf001": {"status": "completed", "output": "/path/to/sf001_page.html"},
    "sf002": {"status": "completed", "output": "/path/to/sf002_preproc.html"},
    "sf003": {"status": "completed", "output": "/path/to/sf003_3_translations.json"},
    "sf004": {"status": "completed", "output": "/path/to/sf004_translated.html"}
  }
}
```

**ステータス値:**
- `pending`: 未処理
- `completed`: 完了
- `failed`: 処理失敗

中断後、`--resume` オプションで再開すると、完了済みページはスキップされ、未完了・失敗ページのみ再処理されます。

## パフォーマンス考慮事項

SR1000 では以下のポイントに注意してください：

**メモリ管理:**
- Ollama の `keep_alive` パラメータでモデルメモリを管理
- デフォルト `5m` で十分な場合が多い

**大規模 PDF 処理:**
- ページごと独立処理のため、メモリ効率が良好
- 中断・再開可能なため、大規模文書に対応

**翻訳精度:**
- タグ単位処理により正確な翻訳が可能
- 改行は自動的に `<br>` に変換される
- テンプレート `temperature` を調整可能

**初回実行:**
- Docling がモデルをダウンロード（時間がかかる場合あり）
- 2 回目以降は大幅に高速化

詳細は `/workspace/session-state/files/` の最適化ガイドを参照してください。

## ジョブ状態の確認

進捗状況は ログファイルで確認できます：

```bash
tail -f ./work/log.txt
```

ページ処理の詳細な状態は状態ファイルで確認：

```bash
cat ./work/states/page_000001.json
```

**進捗監視スクリプト（リアルタイム表示）:**

以下のスクリプトを使用して、**大分類フェーズ表示（SF001-SF004）+ Ollama 翻訳フェーズの逐次確認**ができます：

```bash
# リアルタイム進捗表示（全フェーズ）
python -m impl_translator.src.features.SR1000.progress_monitor \
  --working-dir ./work

# SF003（翻訳）フェーズのみフィルタ
python -m impl_translator.src.features.SR1000.progress_monitor \
  --working-dir ./work \
  --filter sf003

# ページ処理状態のサマリー表示
python -m impl_translator.src.features.SR1000.progress_monitor \
  --working-dir ./work \
  --summary
```

**進捗監視スクリプトの出力例:**

```
✅ page_000001      PDF→HTML  完了
✅ page_000001      前処理    完了
🔄 page_000001      翻訳      Batch 3/5
⏳ page_000002      PDF→HTML  -
```

**ステータス表示:**
- `✅`: 完了
- `❌`: 失敗
- `🔄`: 処理中
- `⏳`: 未処理


# LLM関係コマンド

** 以下の docker コマンドは WSL 環境で実行する、本プロジェクトのdevcontainer環境からは実行しない **

## GPU認識確認

```bash
docker compose exec ollama nvidia-smi
```

## モデルの取得

```bash
docker compose exec ollama ollama pull qwen3:8b
```

## モデルの実行
```bash
docker compose exec ollama ollama run qwen3:8b
```

## 実行中モデルの確認

```bash
docker compose exec ollama ollama ps
```

## Ollama の再起動（keep_alive=0 環境変数を反映）

```bash
# Ollama コンテナのみ再起動
docker compose restart ollama

# または、全コンテナを再起動
docker compose down
docker compose up -d

# 再起動確認
docker compose logs ollama | head -20
```

## Ollama のステータス確認

### 実行中のモデル確認
```bash
curl http://ollama:11434/api/ps
```

### サーバーバージョン確認
```bash
curl http://localhost:11434/api/version
```

### キャッシュ効率の確認（同じプロンプトで2回実行）
```bash

# jq インストール
apt update
apt install -y jq

# 1回目：初回実行
curl http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "prompt": "Hello",
    "stream": false,
    "keep_alive": "30m"
  }' | jq '.prompt_eval_cached_count, .prompt_eval_count'

# 2回目：キャッシュから読み込まれているか確認
curl http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "prompt": "Hello",
    "stream": false,
    "keep_alive": "30m"
  }' | jq '.prompt_eval_cached_count, .prompt_eval_count'
```

### ログの確認
```bash
# Ollama コンテナのログをリアルタイムで表示
docker compose logs -f ollama
```

## Docling を使用した PDF to HTML 変換

PDF を英語のままHTML化するステップ：

### 1ページごとにHTML化（index.json で管理）

**コマンドライン:**
```bash
python -m impl_translator.src.libs.docling_converter \
  --input-pdf input.pdf \
  --working dir=/output \
  --split-pages
```

出力構造:
```
/output/
├── index.json              # ページ管理メタデータ
└── input_pages/
    ├── page_0001.html
    ├── page_0002.html
    └── ...
```

**Python コード:**
```python
from pathlib import Path
from impl_translator.src.libs.docling_converter import convert_pdf_to_html

pages_dir = convert_pdf_to_html(
    input_pdf=Path("input.pdf"),
    output_dir=Path("/output"),
    split_pages=True
)
```

### 1ファイルに統合

**コマンドライン:**
```bash
python -m impl_translator.src.libs.docling_converter \
  --input-pdf input.pdf \
  --working dir=/output \
  --combine
```

出力:
```
/output/
└── input.html
```

**Python コード:**
```python
from pathlib import Path
from impl_translator.src.libs.docling_converter import convert_pdf_to_html

html_file = convert_pdf_to_html(
    input_pdf=Path("input.pdf"),
    output_dir=Path("/output"),
    combine=True
)
```

### index.json フォーマット

```json
{
  "source_pdf": "/path/to/input.pdf",
  "total_pages": 10,
  "pages": [
    {
      "page_number": 1,
      "file": "page_0001.html",
      "size_bytes": 15234
    },
    ...
  ]
}
```

## HTML 前処理（スタイルタグ削除とID付与）

HTML から翻訳対象外のスタイルタグを削除し、全タグに順序付きIDを付与します。後続の翻訳処理で、このIDを使用して翻訳箇所の特定と復元を行います。

### 削除対象タグ
- 完全削除: `script`
- コンテンツ保持で削除: `b`, `strong`, `i`, `em`, `span`, `font`, `u`

### コマンドライン

```bash
python -m impl_translator.src.libs.html_preproc \
  --input input.html \
  --output preprocessed.html
```

**入力例:**
```html
<p>This is <b>bold</b> and <span>span</span> text.</p>
<script>console.log("remove");</script>
```

**出力例:**
```html
<html id="tag_000000">
<head id="tag_000001">...</head>
<body id="tag_000002">
<p id="tag_000003">This is bold and span text.</p>
</body>
</html>
```

### Python コード

```python
from pathlib import Path
from impl_translator.src.libs.html_preproc import preprocess_html

output_path = preprocess_html(
    input_html=Path("input.html"),
    output_html=Path("preprocessed.html")
)
```

## Ollama API クライアント

Ollama サーバーへのテキスト生成リクエストを簡単に行うクライアントです。

### Python コードでの使用

```python
from impl_translator.src.libs.ai_client import OllamaClient

# クライアント初期化
client = OllamaClient(
    host="http://ollama:11434",
    model="qwen3:8b",
    timeout=300
)

# テキスト生成
response = client.generate(
    prompt="Translate into Japanese: Hello world",
    temperature=0.7,
    keep_alive="5m"
)
print(response)

# チャット形式
response = client.chat(
    messages=[
        {"role": "user", "content": "What is 2 + 2?"}
    ],
    temperature=0.7
)
print(response)

# モデル情報取得
info = client.get_model_info()

# 利用可能モデルリスト
models = client.list_models()

# モデルをメモリからアンロード（GPU メモリ解放）
client.unload_model()
```

### コマンドラインでの使用

**テキスト生成:**
```bash
python -m impl_translator.src.libs.ai_client generate \
  --host http://ollama:11434 \
  --model qwen3:8b \
  --prompt "Translate into Japanese: Hello world" \
  --temperature 0.7 \
  --keep-alive "5m"
```

**チャット:**
```bash
python -m impl_translator.src.libs.ai_client chat \
  --host http://ollama:11434 \
  --model qwen3:8b \
  --message "What is 2 + 2?" \
  --temperature 0.7
```

**利用可能モデルリスト:**
```bash
python -m impl_translator.src.libs.ai_client list-models \
  --host http://ollama:11434
```

**モデル情報:**
```bash
python -m impl_translator.src.libs.ai_client model-info \
  --host http://ollama:11434 \
  --model qwen3:8b
```

**モデルをアンロード:**
```bash
python -m impl_translator.src.libs.ai_client unload \
  --host http://ollama:11434 \
  --model qwen3:8b
```

### OllamaClient API リファレンス

**初期化:**
```python
OllamaClient(
    host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    timeout: int = 300
)
```

**メソッド:**

- `generate(prompt, system=None, temperature=0.7, keep_alive="5m", stream=False) -> str`
  - テキスト生成
  
- `chat(messages, system=None, temperature=0.7, keep_alive="5m") -> str`
  - チャット形式での対話
  
- `get_model_info() -> dict`
  - 現在のモデル情報を取得
  
- `list_models() -> list[dict]`
  - 利用可能なモデルリストを取得
  
- `unload_model() -> None`
  - モデルをメモリからアンロード（GPU メモリ解放）

## SR1000 翻訳パイプライン用ユーティリティ

### HTML テキスト抽出（タグ単位）

プリプロセス済みHTML からタグ単位でテキストを抽出します。

**コマンドライン:**
```bash
python -m impl_translator.src.libs.html_text_extractor \
  --input preprocessed.html \
  --output extracted.txt
```

**出力フォーマット:**
```
{ID=tag_000000} {タグ内のテキスト全て}
{ID=tag_000001} {タグ内のテキスト全て}
{ID=tag_000002} {タグ内のテキスト全て}
```

**Python コード:**
```python
from pathlib import Path
from impl_translator.src.libs.html_text_extractor import extract_tag_text, format_as_text_lines

text_lines = extract_tag_text(Path("preprocessed.html"))
formatted = format_as_text_lines(text_lines)
print(formatted)
```

### テキストをバッチに分割（1500文字区切り）

抽出したテキストを翻訳用バッチに分割します。

**コマンドライン:**
```bash
python -m impl_translator.src.libs.batch_splitter \
  --input extracted.txt \
  --output batches.json \
  --max-chars 1500
```

**出力フォーマット:**
```json
[
  {
    "batch_id": 0,
    "lines": [
      {"id": "tag_000000", "text": "..."},
      {"id": "tag_000001", "text": "..."}
    ],
    "char_count": 1234
  },
  ...
]
```

**Python コード:**
```python
from pathlib import Path
from impl_translator.src.libs.batch_splitter import split_text_into_batches, format_batch_for_translation

batches = split_text_into_batches(Path("extracted.txt"), max_chars=1500)
for batch in batches:
    formatted = format_batch_for_translation(batch)
    # Send to translation API
    print(f"Batch {batch['batch_id']}: {batch['char_count']} chars")
```

### バッチを Ollama で翻訳（SF003）

バッチを Ollama API で翻訳し、翻訳結果を JSON 形式で出力。改行は `<br>` に変換。

**入力形式（batch_splitter の出力）:**
```json
[
  {
    "batch_id": 0,
    "lines": [
      {"id": "tag_000000", "text": "Hello world"},
      {"id": "tag_000001", "text": "This is a test\nwith newline"}
    ],
    "char_count": 35
  }
]
```

**処理の流れ:**
1. バッチを Ollama API 送信用フォーマットに変換
   ```
   {ID=tag_000000} Hello world
   {ID=tag_000001} This is a test<br>with newline
   ```
2. Ollama で翻訳実行
3. 応答を解析し ID -> 翻訳テキストのマッピングを作成
4. JSON 形式で保存

**コマンドライン:**
```bash
python -m impl_translator.src.libs.translation_formatter \
  --input batches.json \
  --output translations.json \
  --host http://localhost:11434 \
  --model qwen3:8b \
  --temperature 0.3
```

**出力フォーマット:**
```json
{
  "total_batches": 1,
  "translations": {
    "tag_000000": "こんにちは世界",
    "tag_000001": "これはテストです<br>改行を含む"
  }
}
```

**メタデータ付き出力:**
```bash
python -m impl_translator.src.libs.translation_formatter \
  --input batches.json \
  --output translations.json \
  --metadata
```

**単一バッチの翻訳:**
```bash
python -m impl_translator.src.libs.translation_formatter \
  --input batches.json \
  --output batch_0_translations.json \
  --single-batch 0
```

**Python コード:**
```python
from pathlib import Path
from impl_translator.src.libs.translation_formatter import translate_batches, translate_batch

# 全バッチを翻訳
result = translate_batches(
    input_batches_json=Path("batches.json"),
    output_translations_json=Path("translations.json"),
    ollama_host="http://localhost:11434",
    model="qwen3:8b",
    temperature=0.3
)
print(f"Total batches: {result['total_batches']}")
print(f"Total translations: {len(result['translations'])}")

# または単一バッチを翻訳
batch = batches[0]
translations = translate_batch(
    batch,
    ollama_host="http://localhost:11434",
    model="qwen3:8b"
)
print(translations)
```

### 翻訳済みテキストを HTML に復元

翻訳済みのテキストを ID マッピングで元の HTML に戻します。

**コマンドライン:**
```bash
python -m impl_translator.src.libs.translation_restorer \
  --input-html preprocessed.html \
  --translations translations.json \
  --output translated.html
```

**入力フォーマット（translations.json）:**
```json
{
  "tag_000000": "翻訳済みテキスト",
  "tag_000001": "別の翻訳済みテキスト",
  ...
}
```

**Python コード:**
```python
from pathlib import Path
from impl_translator.src.libs.translation_restorer import restore_translations_to_html, load_translations_from_text

# JSON ファイルから復元
restore_translations_to_html(
    input_html=Path("preprocessed.html"),
    translations_json=Path("translations.json"),
    output_html=Path("translated.html")
)

# またはテキスト形式から復元
translations_text = "{ID=tag_000000} 翻訳済みテキスト\n..."
translations_dict = load_translations_from_text(translations_text)
```

### SR1000 フロー全体の例

```bash
# 1. PDF → 1ページ毎 HTML
python -m impl_translator.src.libs.docling_converter \
  --input-pdf input.pdf \
  --working dir=/tmp/step1 \
  --split-pages

# 2. HTML → スタイルタグ削除 + ID付与
python -m impl_translator.src.libs.html_preproc \
  --input /tmp/step1/input_pages/page_0001.html \
  --output /tmp/step2/page_0001_preproc.html

# 3. HTML → テキスト抽出（タグ単位）
python -m impl_translator.src.libs.html_text_extractor \
  --input /tmp/step2/page_0001_preproc.html \
  --output /tmp/step3/page_0001_extracted.txt

# 4. テキスト → バッチ分割
python -m impl_translator.src.libs.batch_splitter \
  --input /tmp/step3/page_0001_extracted.txt \
  --output /tmp/step4/page_0001_batches.json

# 5. バッチ → Ollama で翻訳（SF003）
python -m impl_translator.src.libs.translation_formatter \
  --input /tmp/step4/page_0001_batches.json \
  --output /tmp/step5/page_0001_translations.json \
  --host http://localhost:11434 \
  --model qwen3:8b \
  --temperature 0.3

# 6. 翻訳済みテキスト → HTML に復元
python -m impl_translator.src.libs.translation_restorer \
  --input-html /tmp/step2/page_0001_preproc.html \
  --translations /tmp/step5/page_0001_translations.json \
  --output /tmp/step6/page_0001_translated.html
```

## APIでの翻訳実行

```bash
curl http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "prompt": "Translate into Japanese: The surface consists of multiple polygons.",
    "stream": false,
    "think": false
  }'
```

# PDFMathTranslate-next

## PDF翻訳実行
```bash
pdf2zh_next input/odb_spec_user.pdf \
    --ollama \
    --ollama-host http://ollama:11434 \
    --ollama-model qwen3:8b \
    --lang-in en \
    --lang-out ja \
    --qps 1 \
    --pages 1-5 \
    --output output
```

## GUIでの翻訳実行
```bash
pdf2zh_next --gui
```

## 翻訳プロンプト設定

```text
/no_think

You are a professional English-to-Japanese
technical translator specializing in PCB and CAM.

Preserve identifiers, file names, commands,
coordinates, numerical values, and units.

Do not summarize or omit any information.
Output only the Japanese translation.
```

# GUI起動

## 開発モード（推奨）

### デフォルトディレクトリ（output/job）
```bash
cd /workspace
PYTHONPATH=/workspace python -m flask --app impl_translator.src.app.app run
```

### カスタムジョブディレクトリを指定
```bash
cd /workspace
PYTHONPATH=/workspace IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
python -m flask --app impl_translator.src.app.app run
```

**例：odbpp_translatol プロジェクト**
```bash
cd /workspace
IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
PYTHONPATH=/workspace python -m flask --app impl_translator.src.app.app run
```

その後 `http://localhost:5000/sr1001/` でジョブID `31b4adf2021a427598ca3f90ede26a1b` を入力して確認

## 本番モード（Gunicorn）
```bash
# Gunicorn インストール
python -m pip install gunicorn

# デフォルトディレクトリ
cd /workspace
PYTHONPATH=/workspace gunicorn -w 4 -b 0.0.0.0:5000 "impl_translator.src.app:create_app()"

# カスタムジョブディレクトリを指定
cd /workspace
IMPL_TRANSLATOR_WORKING_DIR="_data/odbpp_translatol/output/job" \
PYTHONPATH=/workspace gunicorn -w 4 -b 0.0.0.0:5000 "impl_translator.src.app:create_app()"
```

## 直接実行（非推奨）
```bash
cd /workspace
PYTHONPATH=/workspace python impl_translator/src/app/app.py
```

**アクセス先：** `http://localhost:5000/sr1001/`
