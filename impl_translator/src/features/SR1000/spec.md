
# 機能
英語PDFを日本語に翻訳する機能

## 使い方
```bash
# 実行
python -m impl_translator.src.features.SR1000.batch --working-dir=output/job --log-file=output/job/log.txt --input-pdf=input/english.pdf --output-pdf=output/japanese.pdf --output-text=output/japanese.txt
# 開始時に job_id とログファイルの場所が表示される
# 終了や中断をすると job_id と、出力フォルダが表示される

# 再開
python -m impl_translator.src.features.SR1000.batch --working-dir=output/job --resume --job-id=<job_id>

```

## 処理
- ポリシー
  - データ出力は人が見るのでYAML形式
  - 出力のテキストは改行の通常テキストで良い
  - SR1000はpdf2zh_nextを直接呼び出さず、別のモジュールを介して翻訳する
- 入力
  - 英語PDF
- 処理
  - metadata作成、開始時間、経過時間、入力ファイルのサイズ日付、ページ数、LLMモデル情報など
  - 1ページ単位で処理を実施
    - ローカルモデルが長文に適さない場合があるので、適宜分割して処理する
    - 1ページ毎に結果と処理時間、処理テキスト量、LLM応答ステータスなど、metadataを保存する
  - ページ整合
    - 処理結果が元のPDFのページ順序と一致しているか確認する
  - 図形、画像の扱い
    - 図形＋注釈テキストが分かれており翻訳可能なら翻訳する
    - 画像はそのままで良い
- 翻訳エラー時
  - エラーをmetadataに記録し、処理を継続
  - 次の文章、又は次のページの処理に進む
  - 翻訳に失敗したページは、出力PDFの対応する位置に失敗した旨を表示するページを配置する
- 処理の再開
  - ページ単位で再開可能、1ページを分割して処理していた場合、その分は保存されない、ページ単位で再処理される
  - 翻訳に失敗したページも再開時に再処理する
  - 中断した場合、指定された working-dir と job_id から保存されたmetadataを読み込み、それをもとに処理を再開する
  - LLMモデル変更などあってもそのまま再開して良い
- 出力
  - 処理全体のmetadata
  - ページ毎のmetadata
  - 日本語PDF
  - 日本語テキスト
  - ログ（tail -f 進捗確認用） job機能とは別にログを出す
