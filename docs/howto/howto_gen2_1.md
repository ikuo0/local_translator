
# 手法の大幅変更
- 英語PDFをHTML化
- HTMLをページ毎に出力
  - 作業ディレクトリに index.json を作成し、出力管理
- HTML と対になるテキストを生成
  - BeautifulSoup を使用してHTMLからテキストを抽出
- ページ毎に翻訳
  - この時に Ollama に大して keep_alive を 0 で指定しキャッシュを使わないようにする
- 翻訳結果をHTMLに反映
- HTMLからPDFを生成
  - フォント: `Noto Sans CJK JP` を使用
