

# 処理概要

- SR1000
  - PDFの英語→日本語翻訳実行
  - SF001_to_html
    - PDFを1ページ毎にHTML化する
  - SF002_preproc
    - HTMLからスタイルタグを削除し、IDを付与する
  - SF003_translate
    - HTMLからタグ単位でテキストを抽出し、分割して日本語に翻訳した結果をIDごとに収集する。
    - [SF003_translate の詳細仕様](features/SR1000/spec.md#sf003_translate)
  - SF004
    - ID別にテキストを復元しHTMLとして保存（翻訳元とは別ファイルで保存）
  - SF005
    - SF004で作成したHTMLをまとめ、`SF005/pdf/入力ファイル名jpn.pdf` に保存する
    - `SF005/text/page_000001.txt` のようにページごとのテキストを保存する
    - 図はページ内の出現順に `[[figure1]]` などで示し、表は `[[table begin]]` と `[[table end]]` で囲む。段組や改行などのレイアウト上の区切りは半角空白にする
    - SF001の原文HTMLとSF004の翻訳HTMLをMarkdownに変換し、それぞれ `SF005/md_en/page_000001.md` と `SF005/md_jp/page_000001.md` のように保存する
- SR1001
  - SR1000 の進捗をUIから確認する
- SR1100
  - フリー翻訳機能
  - UIを用意し、英語⇔日本語の翻訳をする
  - 用途を翻訳に限定し、自由な質問は受け付けない
  - bedrockなどで言うところの system 部を設けて翻訳機能以外の質問を制御する
- SR1200
  - フリー問い合わせ機能
  - UIを用意し、ＡＩに好きに質問できるようにする
