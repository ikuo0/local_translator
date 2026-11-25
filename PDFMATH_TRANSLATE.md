# PDFMathTranslate-next の使い方

Dev Container 内で `pdf2zh_next` を直接使う場合の手順です。

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

GUI は `pdf2zh_next --gui` で起動します。VS Code の「ポート」ビューで GUI のポートを転送し、Windows のブラウザーで開きます。

## PCB/CAM 向け翻訳プロンプト例

```text
/no_think

You are a professional English-to-Japanese
technical translator specializing in PCB and CAM.

Preserve identifiers, file names, commands,
coordinates, numerical values, and units.

Do not summarize or omit any information.
Output only the Japanese translation.
```
