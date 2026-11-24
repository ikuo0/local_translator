`pdf2zh_next` のソースコードを直接修正せずに解決するなら、**Ollama APIの手前に軽量なプロキシを配置して、**`keep_alive`**&#x20;を上書きする方法**があります。

Ollamaではリクエストに含まれる `keep_alive` が環境変数 `OLLAMA_KEEP_ALIVE` より優先されるため、環境変数だけでは解決できません。

## **1. APIプロキシ方式**

**pdf2zh_next**

既存コードのまま

HTTPリクエスト（keep_alive: 既定値）

**Ollama API Proxy**

keep_alive を 0 に上書き

HTTPリクエスト（keep_alive: 0）

**Ollama / Qwen3 8B**

`pdf2zh_next` 側では接続先URLを変更するだけで済みます。外部ライブラリを直接修正しないという開発ポリシーにも適合します。

ただし、調べたところ、プロキシを作る必要すらない可能性があります。

## **2. OpenAI互換APIを利用する（推奨）**

OllamaはネイティブAPI以外にOpenAI互換APIを提供しています。また、PDFMathTranslate-nextはOpenAI形式の翻訳エンジンに正式対応しています。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



つまり、Ollama専用の翻訳エンジンを使用しなければよいという考え方です。

現在の設定：

```
--ollama \
--ollama-host http://ollama:11434 \
--ollama-model qwen3:8b
```

変更案：

```
--openai \
--openai-base-url http://ollama:11434/v1 \
--openai-model qwen3:8b \
--openai-api-key dummy
```

Docker Compose側：

```
environment:
  OLLAMA_KEEP_ALIVE: "0"
  OLLAMA_NUM_PARALLEL: "1"
  OLLAMA_MAX_LOADED_MODELS: "1"
```

OpenAIの標準APIには `keep_alive` パラメータがないため、Ollama側の環境変数を適用できる可能性が高いです。

OpenAIのAPIキーは不要で、通信もローカルで完結します。

実際に翻訳後にアンロードされるかは、以下で確認してください。

```
watch -n 1 'docker compose exec -T ollama ollama ps'
```

## **3. ページ単位で外部からアンロードする**

既に1ページずつ翻訳する仕組みを実装しているのであれば、翻訳完了後に次の処理を挟む方法もあります。

```
requests.post(    "http://ollama:11434/api/generate",    json={        "model": "qwen3:8b",        "keep_alive": 0,    },    timeout=30,).raise_for_status()
```

これなら `pdf2zh_next` が内部で指定している `keep_alive` に関係なく、ページ完了後にモデルを解放できます。

## **解決策の比較**

| 方法          | OSS改変 | 追加実装 | 解放単位    |
| ----------- | ----- | ---- | ------- |
| OpenAI互換API | 不要    | 不要   | リクエスト単位 |
| ページ完了後の解放   | 不要    | 数行   | ページ単位   |
| APIプロキシ     | 不要    | 小規模  | リクエスト単位 |
| OSS直接修正     | 必要    | 数行   | リクエスト単位 |

まずは**OpenAI互換APIへの切り替え**を試すことを推奨します。

ただし、翻訳品質やプロンプト処理が変わる可能性もあるため、現在の翻訳エンジンを維持したいのであれば、ページ完了後のアンロードが最も簡単です。

なお、Ollama公式仕様でも、APIの `keep_alive` が環境変数より優先されることが明記されています。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1
