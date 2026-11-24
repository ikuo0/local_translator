# Qwen3 8B 翻訳処理の高速化設定ガイド

## 現在の設定分析

### 現在のボトルネック

```python
TranslationSettings(
    qps=1,                          # ❌ デフォルト: 4 (大幅に制限中)
    pool_max_workers=1,             # ❌ 並列処理が無効
    custom_system_prompt="/no_think",  # ✅ Thinking 無効化済み
    no_auto_extract_glossary=True,  # ✅ 用語抽出スキップ済み
)

PDFSettings(
    no_dual=True,                   # ✅ デュアルページモード無効
)
```

---

## 高速化に寄与する設定オプション

### 1. **QPS (Queries Per Second) の増加** ⚡ 最も効果的

| 設定 | 現在 | 推奨 | 効果 |
|------|------|------|------|
| `qps` | 1 | 4-8 | **4～8倍高速化** ⭐⭐⭐ |

**説明：**
- 1秒あたりにLLMに送信するリクエスト数
- Ollama のリソース（メモリ/CPU）に応じて調整
- ローカル Ollama サーバーの場合、4～8が安全な値

**注意：**
- Ollama サーバーの負荷が上がる
- メモリ不足でクラッシュする可能性があるため、段階的に増加推奨

**調整方法：**
```python
# 段階的に試す
qps=2   # 2倍速
qps=4   # 4倍速（デフォルト値）
qps=8   # 8倍速（高負荷）
```

---

### 2. **Worker プール最大数** ⚡ 次に効果的

| 設定 | 現在 | 推奨 | 効果 |
|------|------|------|------|
| `pool_max_workers` | 1 | 2-4 | **2～4倍の並列処理** ⭐⭐ |

**説明：**
- 同時に翻訳リクエストを処理するワーカースレッド数
- CPU コア数の 2～4 倍が目安

**調整方法：**
```python
pool_max_workers=2   # シングルコアマシン
pool_max_workers=4   # デュアルコアマシン
pool_max_workers=8   # クアッドコア以上
```

---

### 3. **用語抽出とキャッシング** 🔄

| パラメータ | 現在 | 推奨 | 効果 |
|-----------|------|------|------|
| `no_auto_extract_glossary` | True | ✅ True | 初回処理高速化 |
| `ignore_cache` | False | ✅ False | 2回目以降高速化 |
| `save_auto_extracted_glossary` | False | 要検討 | 用語抽出の再利用 |

**説明：**
- `no_auto_extract_glossary=True` - 自動用語抽出をスキップ（既に設定済み ✅）
- `ignore_cache=False` - キャッシュを活用（デフォルト、すでに有効）
- `save_auto_extracted_glossary=True` - 抽出された用語を保存して再利用

---

### 4. **テキスト処理の最適化** 🎯

| パラメータ | デフォルト | 推奨 | 効果 |
|-----------|----------|------|------|
| `min_text_length` | 5 | 10-20 | 短すぎるテキスト翻訳スキップ |
| `skip_clean` | False | True | テキストクリーニング省略 |
| `disable_rich_text_translate` | False | True | リッチテキスト処理省略 |

**説明：**
- `min_text_length` - この文字数未満のテキストは翻訳対象外
  - デフォルト 5 → 推奨 10-20（短すぎるテキストをスキップ）
- `skip_clean` - テキストクリーニング処理をスキップ
  - 軽度の汚れなら無効にして時間短縮
- `disable_rich_text_translate` - リッチテキスト処理を無効化
  - テキストのみのPDFなら推奨

---

### 5. **Term翻訳の最適化** 📝

| パラメータ | デフォルト | 推奨 | 効果 |
|-----------|----------|------|------|
| `term_qps` | None（無制限） | 2-4 | 専門用語翻訳の並列制御 |
| `term_pool_max_workers` | None | 2-4 | 専門用語ワーカー数 |

**説明：**
- 用語辞書がある場合、専門用語翻訳の速度を制御
- 通常は設定不要（None で自動管理）

---

## 推奨設定（段階的改善）

### ステップ 1: 保守的な改善（リスク低）

```python
TranslationSettings(
    lang_in="en",
    lang_out="ja",
    output=str(output_dir),
    qps=2,                          # 1 → 2 (2倍速)
    pool_max_workers=2,             # 1 → 2 (並列化開始)
    custom_system_prompt="/no_think",
    no_auto_extract_glossary=True,
    min_text_length=10,             # 短テキスト省略
),
PDFSettings(
    no_dual=True,
    skip_clean=True,                # クリーニング省略
),
```

**期待効果：** 2～3倍高速化

---

### ステップ 2: 中程度の改善（リスク中）

```python
TranslationSettings(
    qps=4,                          # 1 → 4 (4倍速)
    pool_max_workers=4,             # 1 → 4 (並列化強化)
    custom_system_prompt="/no_think",
    no_auto_extract_glossary=True,
    min_text_length=15,
),
PDFSettings(
    no_dual=True,
    skip_clean=True,
    disable_rich_text_translate=True,
),
```

**期待効果：** 4～6倍高速化
**注意：** Ollama サーバーの負荷が上がる

---

### ステップ 3: アグレッシブな改善（リスク高）

```python
TranslationSettings(
    qps=8,                          # 1 → 8 (8倍速)
    pool_max_workers=8,             # 1 → 8 (最大並列化)
    custom_system_prompt="/no_think",
    no_auto_extract_glossary=True,
    min_text_length=20,
),
PDFSettings(
    no_dual=True,
    skip_clean=True,
    disable_rich_text_translate=True,
),
```

**期待効果：** 6～10倍高速化
**注意：** メモリ不足やタイムアウトのリスク

---

## 実装方法

### 修正対象ファイル

**`impl_translator/src/libs/translator/__init__.py`**

```python
def translate_page(
    input_pdf: Path,
    output_dir: Path,
    host: str,
    model: str,
    interrupt_handler=None,
    qps: int = 4,                   # パラメータ化
    pool_max_workers: int = 2,      # パラメータ化
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = SettingsModel(
        basic=BasicSettings(input_files={str(input_pdf)}),
        translation=TranslationSettings(
            lang_in="en",
            lang_out="ja",
            output=str(output_dir),
            qps=qps,                                # 動的設定
            pool_max_workers=pool_max_workers,      # 動的設定
            custom_system_prompt="/no_think",
            no_auto_extract_glossary=True,
            min_text_length=10,                     # 追加
        ),
        pdf=PDFSettings(
            no_dual=True,
            skip_clean=True,                        # 追加
            disable_rich_text_translate=True,       # 追加
        ),
        translate_engine_settings=OllamaSettings(
            ollama_host=host,
            ollama_model=model
        ),
    )
    # ... rest of code
```

---

## パフォーマンス測定

各設定での実行時間を測定：

```bash
# ステップ 1: 保守的な設定
time python -m impl_translator.src.features.SR1000.batch \
  --working-dir output/job \
  --log-file output/job/log.txt \
  --input-pdf input/english.pdf \
  --output-pdf output/japanese_step1.pdf \
  --output-text output/japanese_step1.txt

# ステップ 2: 中程度の設定
time python -m impl_translator.src.features.SR1000.batch \
  --working-dir output/job2 \
  --log-file output/job2/log.txt \
  --input-pdf input/english.pdf \
  --output-pdf output/japanese_step2.pdf \
  --output-text output/japanese_step2.txt
```

**測定ポイント：**
- 総実行時間
- メモリ使用量 (`top` / `htop` で確認)
- Ollama サーバーの CPU/メモリ使用率

---

## まとめ

| 施策 | 効果 | 実装難度 | 推奨度 |
|------|------|--------|-------|
| `qps` 増加 | ⭐⭐⭐ | 簡単 | ⭐⭐⭐ |
| `pool_max_workers` 増加 | ⭐⭐ | 簡単 | ⭐⭐⭐ |
| `min_text_length` 設定 | ⭐ | 簡単 | ⭐⭐ |
| `skip_clean` 有効化 | ⭐ | 簡単 | ⭐⭐ |
| `disable_rich_text_translate` 有効化 | ⭐ | 簡単 | ⭐ |

**最初に試すべき組み合わせ：**
```python
qps=4, pool_max_workers=2  # 2～3倍高速化（推奨スタート）
```

その後、Ollama サーバーの負荷を監視しながら段階的に増加させることをお勧めします。
