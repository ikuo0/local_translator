# CTRL+C 中断機能の修正説明

## 問題点
元のコードで CTRL+C (KeyboardInterrupt) に対応できない主な理由：

1. **signal ハンドリングが不完全** 
   - Python のデフォルトの KeyboardInterrupt は、メインスレッド以外では反応しない
   - 長時間実行される処理（`do_translate_file()`など）では中断できない

2. **ネストされた try-except ブロックの問題**
   - ページ処理のループ内の内側の try-except が `KeyboardInterrupt` を捕捉していない
   - 4～9ページが処理中に中断されると、状態が不完全なまま保存される

3. **状態更新タイミングの問題**
   - ページ処理中に中断されると、ページのステータスが "running" のままになる
   - 次回再開時に不正な状態から開始される可能性がある

## 修正内容

### 1. InterruptionHandler クラスの追加 (batch.py)
```python
class InterruptionHandler:
    """Graceful interruption handler for CTRL+C."""

    def __init__(self):
        self.interrupted = False
        self._previous_handler = None

    def __enter__(self):
        self._previous_handler = signal.signal(signal.SIGINT, self._handle_interrupt)
        return self

    def __exit__(self, *args):
        signal.signal(signal.SIGINT, self._previous_handler)

    def _handle_interrupt(self, signum, frame):
        self.interrupted = True

    def check(self):
        """Check if interruption was requested; raises KeyboardInterrupt if so."""
        if self.interrupted:
            raise KeyboardInterrupt("Interrupted by user")
```

**利点：**
- SIGINT シグナルを捕捉して、フラグを設定する
- コンテキストマネージャーで、前のハンドラーを自動的に復元
- `check()` メソッドで、定期的に中断要求を確認

### 2. run_job() 関数の修正

#### a) InterruptionHandler の有効化
```python
with InterruptionHandler() as interrupt_handler:
    try:
        # 処理...
```

#### b) ページ処理ループの各所で中断チェック
```python
for page_number in range(1, len(source) + 1):
    interrupt_handler.check()  # ← 新しいページ処理前に確認
```

#### c) translator.translate_page() 呼び出し時に interrupt_handler を渡す
```python
translated = translator.translate_page(
    page_input,
    temporary / "translated",
    data["ollama_host"],
    data["ollama_model"],
    interrupt_handler,  # ← 渡すようにした
)
```

#### d) ページ処理中の中断を適切に処理
```python
except KeyboardInterrupt:
    page_info["status"] = "interrupted"  # ← 状態を明確に記録
    page_info["elapsed_seconds"] = round(
        time.monotonic() - start, 3
    )
    page_info["finished_at"] = job.now()
    job.save(working_dir, job_id, state)  # ← 状態を保存してから再発生
    raise
```

### 3. translator/__init__.py の修正

#### a) スレッド化処理の導入
```python
def translate_page(
    input_pdf: Path,
    output_dir: Path,
    host: str,
    model: str,
    interrupt_handler=None,  # ← オプショナルパラメータ
) -> Path:
```

#### b) ワーカースレッドで翻訳を実行
```python
def translate_worker():
    try:
        error_count = do_translate_file(settings, ignore_error=False)
        error_holder["error_count"] = error_count
    except Exception as error:
        error_holder["exception"] = error

thread = threading.Thread(target=translate_worker, daemon=False)
thread.start()
```

#### c) スレッドの終了を待ちながら、定期的に中断をチェック
```python
while thread.is_alive():
    if interrupt_handler:
        interrupt_handler.check()  # ← 0.1秒ごとに確認
    thread.join(timeout=0.1)
```

**利点：**
- メインスレッドが CTRL+C に応答可能
- 長時間実行タスク中でも定期的に中断要求を確認
- 子スレッドは自然に終了まで実行される（無理やり中断しない）

## 再開時の動作

中断後に `--resume` で再開する場合：

1. ステータスが "interrupted" のページは **スキップされず再開される**
2. ステータスが "completed" のページは **スキップされる**
3. ステータスが "failed" のページは **失敗として記録される**
4. ステータスが "running" のページは **エラー状態として記録される**（自動修正されない）

## 使用方法

通常実行時：
```bash
python -m impl_translator.src.features.SR1000.batch \
  --working-dir=output/job \
  --log-file=output/job/log.txt \
  --input-pdf=input/english.pdf \
  --output-pdf=output/japanese.pdf \
  --output-text=output/japanese.txt
```

CTRL+C で中断（1回目）：
- ステータスが "interrupted" で保存される
- 終了コードは 130 (標準的な SIGINT 終了コード)

再開（再度実行またはで）：
```bash
python -m impl_translator.src.features.SR1000.batch \
  --resume \
  --working-dir=output/job \
  --job-id=<JOB_ID>
```

## 状態フロー

```
created
  ↓
running → (各ページ)
  ├─ 完了: completed
  ├─ エラー: failed
  └─ 中断: interrupted (状態保存後、再開可能)
  ↓
completed
├─ 失敗あり: completed_with_errors
└─ 失敗なし: completed
```

中断されたページは、再開時に "running" から "completed" or "failed" に遷移します。
