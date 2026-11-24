# local_translator

ローカルLLM（Ollama）を使って、PDFやテキストなどの長文を日本語に翻訳するCLIです。文書を分割して順に翻訳するため、モデルのコンテキスト長を超える文書も処理できます。PDFから抽出した文章をUTF-8のテキストファイルとして保存します。

## セットアップ

1. [Ollama](https://ollama.com/)をインストールして起動します。
2. 使用するモデルを取得します（例: `ollama pull gemma3`）。
3. Python 3.9以上の環境で依存パッケージをインストールします。

```sh
python -m pip install -r requirements.txt
```

## 使い方

```sh
python translator.py document.pdf
python translator.py document.txt --model gemma3 -o translated.txt
```

出力先を省略すると、入力ファイル名に`_ja.txt`を付けたファイルが作成されます。Ollamaの既定URLは`http://localhost:11434`、チャンクサイズは3000文字です。必要に応じて`--base-url`と`--chunk-size`で変更できます。

```sh
python translator.py document.pdf --base-url http://localhost:11434 --chunk-size 2000
```

スキャン画像のみのPDFは文字を抽出できません。翻訳には、Ollamaで使用するモデルをあらかじめダウンロードし、ローカルで実行できる状態にしてください。
