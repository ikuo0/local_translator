
# ルール
- 以下のファイル構成とする
  - /libs/{module name}/{module name}
  - /libs/{module name}/{module name}/__init__.py
    - import で機能取り込み、公開関数実装
  - /libs/{module name}/{module name}/__main__.py
    - コマンドとして単体実行できるようにする

# 概要
- jobs
  - job_id発行、状態管理など
  - 指定された出力ディレクトリで状態管理をする、DBは使わない
    - /{specify directory}/{job_id}/
- translator
  - 翻訳本体機能
  - pdf2zh_next を用いた翻訳処理
