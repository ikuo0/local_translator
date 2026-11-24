可能です。Windows 11＋WSL2＋Docker＋VSCode DevContainerの構成で、GPUを利用したローカルPDF翻訳環境を構築できます。

構築順序もその認識で合っています。

1. DevContainerからNVIDIA GPUを利用できるようにする
2. Ollamaを起動する
3. Qwen3 8Bをダウンロードし、GPUでの翻訳を確認する
4. PDFMathTranslate-nextをインストールする
5. 翻訳エンジンとしてOllamaを指定する
6. PDFの翻訳を実行する

## **推奨システム構成**

**Windows 11 / WSL2 / Docker**

Docker Compose

**DevContainer（Linux）**

VSCode / Python / PDFMathTranslate-next

HTTP API :11434

**Ollamaコンテナ**

Qwen3 8B / 量子化モデル

**RTX 4060 / VRAM 8GB**

CUDAによる推論

Ollamaと翻訳プログラムを同一コンテナに入れることもできますが、Docker Composeで分離する構成を推奨します。

Ollama側だけGPUを割り当て、翻訳側は通常のPython開発環境として管理できます。将来的に別のLLMへの変更や、PDF以外の翻訳プログラムの追加も容易です。

## **1. プロジェクト構成**

プロジェクト名は `local-pdf-translator` などでよいでしょう。

```
local-pdf-translator/
├── .devcontainer/
│   └── devcontainer.json
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── models/
│   └── Modelfile
├── input/
│   └── odb_spec_user.pdf
├── output/
├── src/
└── .gitignore
```

## **2. DevContainerの構築**

**docker-compose.yml**

```
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - .:/workspace
    working_dir: /workspace
    command: sleep infinity
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    gpus: all
    volumes:
      - ollama_data:/root/.ollama
    environment:
      OLLAMA_NUM_PARALLEL: "1"
      OLLAMA_MAX_LOADED_MODELS: "1"
      OLLAMA_CONTEXT_LENGTH: "4096"
      OLLAMA_KEEP_ALIVE: "-1"
      OLLAMA_FLASH_ATTENTION: "1"
      OLLAMA_NO_CLOUD: "1"

volumes:
  ollama_data:
```

OllamaのモデルはDocker Volumeに保存するので、DevContainerを再構築してもモデルの再ダウンロードは不要です。

`gpus: all` はDocker Compose 2.30.0以降を前提としています。

**Dockerfile**

```
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/requirements.txt
```

**requirements.txt**

```
pdf2zh-next
requests
```

**.devcontainer/devcontainer.json**

```
{
    "name": "Local PDF Translator",
    "dockerComposeFile": "../docker-compose.yml",
    "service": "app",
    "workspaceFolder": "/workspace",
    "forwardPorts": [7860],
    "shutdownAction": "stopCompose",
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python"
            ]
        }
    }
}
```

## **3. Qwen3 8BのGPU動作確認**

ホスト側のターミナルで実行します。

GPUの認識確認：

```
docker compose exec ollama nvidia-smi
```

モデルのダウンロード：

```
docker compose exec ollama ollama pull qwen3:8b
```

モデルの起動：

```
docker compose exec ollama ollama run qwen3:8b
```

別のターミナルから実行状況を確認します。

```
docker compose exec ollama ollama ps
```

`PROCESSOR` が `100% GPU` になっていれば、モデルがGPUに完全に載っています。

### **VRAM使用量の想定**

## **RTX 4060**

**8 GB**

Qwen3 8B（4bit量子化）

約5.2GB

KVキャッシュ・推論領域

約1.0GB

OS・画面表示など

約0.6GB

残り

約1.2GB

4096トークン・同時処理1を想定した概算。実際の使用量は実行環境によって異なります。

並列リクエストを増やすとKVキャッシュの使用量も増えるため、まずは並列数1で運用するのが適切です。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## **4. DevContainerからLLMを利用する**

DevContainer内のターミナルで以下を実行します。

```
curl http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "prompt": "Translate into Japanese: The surface consists of multiple polygons.",
    "stream": false,
    "think": false
  }'
```

ここで日本語訳が返ってくれば、ローカルLLMの環境構築は完了です。

重要なのは、接続先が `localhost` ではなく、Docker Composeのサービス名である `ollama` になる点です。

## **5. PDFMathTranslate-nextの実行**

最初はCLIで動作確認するのがよいでしょう。

```
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

まず5ページだけ翻訳します。問題がなければ `--pages 1-5` を外して全ページを翻訳します。

Web UIを利用する場合は以下です。

```
pdf2zh_next --gui
```

ブラウザで `http://localhost:7860` を開きます。

公式ドキュメント：[PDFMathTranslate-next Web UI](https://pdf2zh-next.com/ja/getting-started/USAGE_webui.html?utm_source=chatgpt.com)

## **6. Qwen3のThinking機能について**

Qwen3は思考モードに対応していますが、翻訳用途では基本的に無効にしたほうがよいです。

余計な推論を行うことで、翻訳時間が延びたり、思考過程が翻訳結果に混入したりする可能性があります。

PDFMathTranslate-nextではカスタムシステムプロンプトも指定できます。`/no_think` を含めたプロンプトの指定が想定されています。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



```
/no_think

You are a professional English-to-Japanese
technical translator specializing in PCB and CAM.

Preserve identifiers, file names, commands,
coordinates, numerical values, and units.

Do not summarize or omit any information.
Output only the Japanese translation.
```

ただし、`/no_think` はソフトな指示なので、APIの `think: false` による無効化のほうが確実です。

## **7. 開発フェーズ**

| フェーズ        | 実装内容                    | 完了条件          |
| ----------- | ----------------------- | ------------- |
| Phase 1     | DevContainer・Ollama構築   | GPU認識         |
| Phase 2     | Qwen3 8B導入              | GPUによる文章翻訳    |
| Phase 3     | PDFMathTranslate-next導入 | 5ページのPDF翻訳    |
| Phase 4     | 翻訳設定の最適化                | 技術用語・レイアウトの確認 |
| Phase 5     | 一括翻訳                    | ODB++仕様書全体の翻訳 |
| Phase 6（任意） | 独自Pythonラッパー開発          | 用語辞書・バッチ処理など  |

初回はモデル、フォント、レイアウト解析用の資産などのダウンロードにインターネット接続が必要ですが、翻訳処理そのものはローカルLLMで完結させられます。

既存のOSSを組み合わせるだけなので、**Phase 5までは独自のPythonプログラムをほとんど書かずに実現できる構成**です。