# local_translator

英語の PDF を Ollama で日本語に翻訳します。Windows 11 をホストとし、Ollama は WSL コンソールから起動します。起動後の API 確認、翻訳、進捗確認は VS Code の Dev Container 内のターミナルで行います。

## 1. Ollama のセットアップと起動

### 推奨スペック

| 項目 | 推奨構成 |
| --- | --- |
| メインメモリ | 64 GB |
| GPU | NVIDIA GPU、VRAM 8 GB 以上 |
| CPU | マルチコア性能に余裕のある CPU。翻訳処理中に、24コアの環境で CPU 使用率が約50%になった実測例があります。 |

### セットアップ手順

Windows に WSL 2、Docker Desktop、VS Code の WSL と Dev Containers 拡張機能を準備します。Docker Desktop で WSL 2 バックエンドと、作業に使うディストリビューションの WSL 統合を有効にします。このリポジトリの Compose 設定は、WSL 2 で利用できる NVIDIA GPU と対応ドライバーが前提です。[Docker Desktop の WSL 設定](https://docs.docker.com/desktop/features/wsl/)・[GPU の要件](https://docs.docker.com/desktop/features/gpu/)

Docker Desktop を起動し、**WSL コンソール**でリポジトリのルートから実行します。

```bash
docker compose version
bash setup/setup_qwen3.sh
```

セットアップは Ollama を起動し、`qwen3:8b` を取得して翻訳を1回実行します。モデルは Docker の `ollama_data` ボリュームに保存されます。セットアップ済みの環境では、WSL コンソールから `docker compose up -d ollama` で起動できます。

同じリポジトリを WSL 側から VS Code で開き、コマンドパレットで **Dev Containers: Reopen in Container** を実行します。[Dev Containers の開き方](https://code.visualstudio.com/docs/devcontainers/containers/)

以降は **Dev Container 内のターミナル**を使います。`/workspace` から、Ollama のバージョンと翻訳応答を確認します。

```bash
cd /workspace
curl -fsS http://ollama:11434/api/version
curl -fsS http://ollama:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3:8b","prompt":"Translate into Japanese: The surface consists of multiple polygons.","stream":false,"think":false}' \
  | python -m json.tool --no-ensure-ascii
```

生成結果の `response` に日本語訳が入っていれば、Dev Container から翻訳を実行できます。

## 2. 翻訳ジョブを実行する

### 新規実行

`./input.pdf` を実際の PDF パスに置き換えます。初回は Docling のモデルを取得するため、処理開始まで時間がかかる場合があります。

```bash
# 実行
INPUT_PDF=./input.pdf
WORK_DIR=./output/job

python -m impl_translator.src.features.SR1000.sr1000_main \
  --input-pdf "$INPUT_PDF" \
  --working-dir "$WORK_DIR" \
  --ollama-host http://ollama:11434 \
  --parallel-count 4

# フルオプション実行
# 新規実行用。再開用の --resume と --job-id は下の例を参照。
python -m impl_translator.src.features.SR1000.sr1000_main \
  --input-pdf "$INPUT_PDF" \
  --working-dir "$WORK_DIR" \
  --ollama-host http://ollama:11434 \
  --ollama-model qwen3:8b \
  --temperature 0.3 \
  --parallel-count 4 \
  --start-page 1 \
  --end-page -1 \
  --system-prompt "ODB++、ガーバーデータ関連の翻訳です" \
  --debug-ollama-cache
```

起動時に表示される `Job ID` を控えます。成果物は `$WORK_DIR/<job_id>/SF005/` に保存されます。
ログは `$WORK_DIR/<job_id>/log.txt`、計測メタデータは `$WORK_DIR/<job_id>/metadata.json` に保存されます。ジョブ ID が決まる前の実行エラーは標準出力に表示されます。

| フォルダ | 成果物 |
| --- | --- |
| `pdf/` | 日本語 PDF。例では `inputjpn.pdf` |
| `text/` | ページ別の日本語テキスト |
| `md_en/` | ページ別の原文 Markdown |
| `md_jp/` | ページ別の日本語 Markdown |

### 中断・失敗したジョブを再開する

`JOB_ID` を控えた値に置き換え、新規実行時と同じ入力 PDF、作業ディレクトリを指定します。全対象ページが翻訳済みの場合も、再開コマンドで成果物を再生成できます。

```bash
JOB_ID='<job_id>'

python -m impl_translator.src.features.SR1000.sr1000_main \
  --input-pdf "$INPUT_PDF" \
  --working-dir "$WORK_DIR" \
  --ollama-host http://ollama:11434 \
  --parallel-count 4 \
  --resume --job-id "$JOB_ID"
```

### 実行オプション

| オプション | 指定する内容 |
| --- | --- |
| `--input-pdf PATH` | 入力 PDF。必須。 |
| `--working-dir DIR` | 各ジョブのフォルダを作成する場所。必須。 |
| `--ollama-host URL` | この環境では `http://ollama:11434` を指定。CLI 既定値は `http://localhost:11434`。 |
| `--ollama-model NAME` | 使用するモデル。既定は `qwen3:8b`。 |
| `--temperature NUMBER` | 翻訳時の生成のばらつき。既定は `0.3`。 |
| `--parallel-count N` | 同時に処理するページ数の上限。既定は `1`。Ollama への翻訳リクエストはジョブ内で1件ずつ送信。 |
| `--start-page N` / `--end-page N` | 1始まりの開始・終了ページ。両端を含む。新規実行で省略すると全ページ、再開時に省略すると保存済みの範囲を使う。 |
| `--system-prompt TEXT` | 各翻訳リクエストに与える補足。例は `--system-prompt "ODB++、ガーバーデータ関連の翻訳です"`。再開時は省略すると保存済みの値を使う。 |
| `--resume --job-id ID` | 指定したジョブの完了済みページを再利用し、残りを処理する。2つのオプションを併用。 |
| `--export-with-fallback` | 失敗ページを原文で補い、PDF・Markdown・テキストを出力する。省略時は、失敗ページが1件でもあれば最終出力を生成しない。 |
| `--debug-ollama-cache` | 翻訳前に Ollama のキャッシュ計測用リクエストを送る。[計測値の読み方](OLLAMA_OPERATIONS.md#翻訳ジョブのキャッシュ診断) |

`--export-with-fallback` を指定しても、失敗ページは `--resume` の再翻訳対象です。原文で補ったページ番号は `job.yaml` の `data.sf005.fallback_pages` に記録され、コマンドの終了コードは `1` です。

## 3. ジョブの経過を確認する

別の Dev Container ターミナルで、同じ `WORK_DIR` と `JOB_ID` を設定します。次のコマンドは実行中のジョブにも使えます。

```bash
cd /workspace
WORK_DIR=./output/job
JOB_ID='<job_id>'

# ページ進捗・経過時間・SF005 の状態を3秒ごとに表示
watch -n 3 python -m impl_translator.src.features.SR1001.batch status \
  --working-dir "$WORK_DIR" --job-id "$JOB_ID"
```

`watch -n 3` を外すと1回だけ表示します。ブラウザーでの確認方法は [SR1001 GUI](JOB_MONITORING.md#sr1001-gui) を参照してください。ログを追う場合は `tail -f "$WORK_DIR/$JOB_ID/log.txt"` を使います。

## 4. テキストを翻訳する（SR1100）

Web UI は [Flask アプリの起動手順](JOB_MONITORING.md#sr1001-gui) と同じアプリから利用できます。ブラウザーで `/sr1100/` を開き、翻訳方向と原文を入力します。

```bash
python -m impl_translator.src.features.SR1100.batch \
  --direction en-ja --text 'The surface consists of multiple polygons.'

printf '%s\n' '複数の多角形で構成されます。' \
  | python -m impl_translator.src.features.SR1100.batch --direction ja-en
```

CLI と Web UI は同じ翻訳処理を使います。翻訳リクエストごとに原文と翻訳方向を送り、Ollama の `keep_alive` は `0` を指定します。

## 5. Ollama に質問する（SR1200）

Flask アプリの `/sr1200/` を開きます。「会話の履歴を引き継ぐ」を有効にすると、同じタブ内の過去の質問と回答を次の問い合わせに含めます。履歴ありでは `keep_alive=30m`、履歴なしでは `keep_alive=0` を指定します。

```bash
python -m impl_translator.src.features.SR1200.batch --text 'PCBとは何ですか？'

# 同じ JSON ファイルを指定して会話を続ける
python -m impl_translator.src.features.SR1200.batch \
  --history-file ./output/sr1200-history.json --text 'PCBとは何ですか？'
python -m impl_translator.src.features.SR1200.batch \
  --history-file ./output/sr1200-history.json --text '先ほどの説明を一文にまとめて'
```

履歴ありのコンテキスト上限は既定で 32,768 トークンです。Web API は Flask 起動時の `SR1200_CONTEXT_TOKENS` 環境変数、CLI は `--context-tokens` で変更できます。Ollama のチャット API で入力トークン数を測り、回答枠を確保するために古い質問と回答から順に除外します。[Ollama チャット API](https://docs.ollama.com/api/chat)

## 関連資料

- [機能と処理の概要](impl_translator/src/overview.md)
- [Ollama の運用・API 診断](OLLAMA_OPERATIONS.md)
- [ジョブの詳細確認と SR1001 GUI](JOB_MONITORING.md)
- [変換・翻訳ツールの単体実行](TRANSLATION_TOOLS.md)
- [PDFMathTranslate-next の使い方](PDFMATH_TRANSLATE.md)

## ローカルで AI を利用する

Ollama の起動後、Dev Container 内のターミナルで `app.py` を起動します。

```bash
cd /workspace
PYTHONPATH=/workspace python impl_translator/src/app/app.py
```

VS Code の「ポート」ビューでコンテナのポート `5000` を転送し、Windows のブラウザーで開きます。別のローカルポートが割り当てられた場合は、ビューに表示されたポートを使います。

- [機能一覧](http://localhost:5000/)
- [テキスト翻訳（SR1100）](http://localhost:5000/sr1100/)
- [Ollama への質問（SR1200）](http://localhost:5000/sr1200/)
