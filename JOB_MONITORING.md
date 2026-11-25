# ジョブの詳細確認と SR1001 GUI

Dev Container 内の `/workspace` で実行します。`WORK_DIR` と `JOB_ID` は翻訳ジョブに合わせて設定します。

```bash
WORK_DIR=./output/job
JOB_ID='<job_id>'
```

## ページ別の進捗と計測値

SR1001 の CLI と Web UI は `job.yaml` を参照します。CLI では次のコマンドで進捗と SF005 の状態を監視できます。

```bash
watch -n 3 python -m impl_translator.src.features.SR1001.batch status \
  --working-dir "$WORK_DIR" --job-id "$JOB_ID"
```

`status --json` は Web UI の API と同じ項目を出力します。ページ別の状態、総処理時間、フェーズ別時間、エラーは `metrics` で確認できます。

ページ処理中は、直近10分間の完了ペースから、実行中と未着手のページにかかる残り時間を概算します。完了記録が4件未満、または完了時刻の間隔が短すぎる間は数値を表示しません。失敗ページの再実行と SF005 の出力時間は見積もりの対象外です。`status --json` では `estimated_remaining_seconds` に秒数が入ります。

```bash
# ページ別の計測値を JSON で表示
python -m impl_translator.src.features.SR1001.batch metrics \
  --working-dir "$WORK_DIR" --job-id "$JOB_ID" --json

# 翻訳段階のログをリアルタイム表示
python -m impl_translator.src.features.SR1000.progress_monitor \
  --working-dir "$WORK_DIR" --job-id "$JOB_ID" --filter sf003

# 保存済みのページ状態を集計
python -m impl_translator.src.features.SR1000.progress_monitor \
  --working-dir "$WORK_DIR" --job-id "$JOB_ID" --summary
```

`summary` と `metrics` は `--json` を指定できます。ページ処理時間の平均・最小・最大・合計は、計測値がある完了済みページが対象です。ジョブ経過時間は作成から最終更新までで、中断中の時間を含みます。並列処理ではページ時間の合計とジョブ経過時間が異なります。

進捗モニターの `--filter` を省略すると全フェーズを表示し、`--no-follow` を加えると追尾せず終了します。表示は ✅ が完了、❌ が失敗、🔄 が処理中、⏳ が未処理です。

## 保存される状態

```bash
cat "$WORK_DIR/$JOB_ID/job.yaml"
cat "$WORK_DIR/$JOB_ID/states/page_000001.json"
```

`job.yaml` の `data.selection` は対象ページ範囲、`data.pages` は1始まりのページ番号ごとの状態、`data.summary` は状態別の件数です。ページの状態は `pending`（未着手）、`progress`（処理中）、`error`（失敗・中断）、`complete`（完了）です。

- `data.pages.<ページ番号>.stats` には、計測できたページの開始・終了時刻、SF001 の開始から最後に処理したフェーズの終了までの秒数、`phases` 内のフェーズ別計測値を記録します。既存ジョブは再開時にページ状態ファイルに保存された計測値を取り込みます。
- `data.sf005` は PDF・テキスト・Markdown 出力の状態です。出力の開始・終了時刻と秒数を `stats` に、成功時のジョブフォルダからの相対パスを `outputs` に、失敗・中断時の理由を `error` に記録します。

`states/page_*.json` には各ページのフェーズ別状態と出力先が記録されます。`--resume` はページ全体が `completed` のページを再利用し、未完了・失敗・状態ファイルがないページは SF001 から処理します。

## SR1001 GUI

Dev Container のターミナルで起動します。

```bash
cd /workspace
IMPL_TRANSLATOR_WORKING_DIR="$WORK_DIR" \
  python -m flask --app impl_translator.src.app.app run --host 0.0.0.0
```

VS Code の「ポート」ビューでコンテナのポート `5000` を転送し、Windows のブラウザーで [SR1001](http://localhost:5000/sr1001/) を開きます。ポートの割り当てが異なる場合は、ビューに表示されたローカルポートを使います。画面にジョブ ID を入力してください。環境変数を省略すると `output/job` が使用されます。

表示は3秒ごとに更新されます。ページ進捗、SF005 の状態と成果物のパス、ページ別・フェーズ別の処理時間を確認できます。旧ジョブで記録がない場合は、表示に「記録なし」または「—」が出ます。

Gunicorn で起動する場合は、Dev Container 内でインストールしたうえでアプリを指定します。

```bash
python -m pip install gunicorn
IMPL_TRANSLATOR_WORKING_DIR="$WORK_DIR" \
  gunicorn -w 4 -b 0.0.0.0:5000 'impl_translator.src.app:create_app()'
```

アプリファイルを直接実行する場合は、`PYTHONPATH=/workspace python impl_translator/src/app/app.py` を使います。
