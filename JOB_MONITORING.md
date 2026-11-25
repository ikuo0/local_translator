# ジョブの詳細確認と SR1001 GUI

Dev Container 内の `/workspace` で実行します。`WORK_DIR` と `JOB_ID` は翻訳ジョブに合わせて設定します。

```bash
WORK_DIR=./output/job
JOB_ID='<job_id>'
```

## ページ別の進捗と計測値

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

進捗モニターの `--filter` を省略すると全フェーズを表示し、`--no-follow` を加えると追尾せず終了します。表示は ✅ が完了、❌ が失敗、🔄 が処理中、⏳ が未処理です。ログ出力先を変更したジョブは、指定したログを `tail -f` で確認できます。

## 保存される状態

```bash
cat "$WORK_DIR/$JOB_ID/job.yaml"
cat "$WORK_DIR/$JOB_ID/states/page_000001.json"
```

`job.yaml` の `data.selection` は対象ページ範囲、`data.pages` は1始まりのページ番号ごとの状態、`data.summary` は状態別の件数です。ページの状態は `pending`（未着手）、`progress`（処理中）、`error`（失敗・中断）、`complete`（完了）です。

`states/page_*.json` には各ページのフェーズ別状態と出力先が記録されます。`--resume` はページ全体が `completed` のページを再利用し、未完了・失敗・状態ファイルがないページは SF001 から処理します。

## SR1001 GUI

Dev Container のターミナルで起動します。

```bash
cd /workspace
IMPL_TRANSLATOR_WORKING_DIR="$WORK_DIR" \
  python -m flask --app impl_translator.src.app.app run --host 0.0.0.0
```

VS Code の「ポート」ビューでコンテナのポート `5000` を転送し、Windows のブラウザーで [SR1001](http://localhost:5000/sr1001/) を開きます。ポートの割り当てが異なる場合は、ビューに表示されたローカルポートを使います。画面にジョブ ID を入力してください。環境変数を省略すると `output/job` が使用されます。

Gunicorn で起動する場合は、Dev Container 内でインストールしたうえでアプリを指定します。

```bash
python -m pip install gunicorn
IMPL_TRANSLATOR_WORKING_DIR="$WORK_DIR" \
  gunicorn -w 4 -b 0.0.0.0:5000 'impl_translator.src.app:create_app()'
```

アプリファイルを直接実行する場合は、`PYTHONPATH=/workspace python impl_translator/src/app/app.py` を使います。
