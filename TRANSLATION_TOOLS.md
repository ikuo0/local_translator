# 変換・翻訳ツールの単体実行

Dev Container 内の `/workspace` で実行します。各モジュールのオプションは `--help` で確認できます。処理の全体像は [overview.md](impl_translator/src/overview.md) を参照してください。

## PDF を HTML に変換する

```bash
python -m impl_translator.src.libs.docling_converter \
  --input-pdf input.pdf --working dir=./html_output --split-pages
```

`--split-pages` は `html_output/index.json` と `html_output/input_pages/page_0001.html` などを出力します。`index.json` には入力 PDF、ページ数、各ページのファイル名とサイズが含まれます。`--combine` に変更すると `html_output/input.html` にまとめます。

## ページ単位で前処理・翻訳・復元する

前の例で出力した1ページを順に処理します。

```bash
python -m impl_translator.src.libs.html_preproc \
  --input html_output/input_pages/page_0001.html --output preprocessed.html

python -m impl_translator.src.libs.html_text_extractor \
  --input preprocessed.html --output extracted.txt

python -m impl_translator.src.libs.batch_splitter \
  --input extracted.txt --output batches.json --max-chars 1500

python -m impl_translator.src.libs.translation_formatter \
  --input batches.json --output translations.json \
  --host http://ollama:11434 --model qwen3:8b --temperature 0.3

python -m impl_translator.src.libs.translation_restorer \
  --input-html preprocessed.html --translations translations.json --output translated.html
```

翻訳時は `--metadata` で計測付き出力、`--single-batch 0` で ID が0のバッチのみを指定できます。復元ツールは ID と翻訳文の対応表を読みます。翻訳ツールが出力する `translations` オブジェクト入りの JSON も使用できます。

### 中間ファイルの確認

- 前処理済み HTML では、`b`、`strong`、`i`、`em`、`span`、`font`、`u` の内容が残り、`script` 要素は内容ごと削除されます。残りの要素には `id000000` から ID が付きます。
- 抽出テキストでは、各行が `id000006 Hello world` のように ID と本文を持ちます。
- `batches.json` は `batch_id`、`lines`、`char_count` を持つバッチの配列です。`lines` の各項目には `id` と `text` があります。
- 翻訳結果 JSON の `translations` は `{"id000006":"こんにちは世界"}` のような対応表です。改行を表す `<br>` は HTML に復元するときに使われます。

## HTML を Markdown に変換する

```bash
python -m impl_translator.src.libs.html_to_markdown \
  --input translated.html --output translated.md
```

## Python から呼び出す

各モジュールの `__init__.py` が公開関数を提供しています。ファイルパスは `pathlib.Path` で渡します。

| モジュール | 公開関数 |
| --- | --- |
| `docling_converter` | `convert_pdf_to_html` |
| `html_preproc` | `preprocess_html` |
| `html_text_extractor` | `extract_tag_text`、`format_as_text_lines` |
| `batch_splitter` | `split_text_into_batches`、`format_batch_for_translation` |
| `translation_formatter` | `translate_batch`、`translate_batches`、`translate_batches_with_metadata` |
| `translation_restorer` | `restore_translations_to_html`、`load_translations_from_text` |
| `html_to_markdown` | `convert_html_to_markdown` |
