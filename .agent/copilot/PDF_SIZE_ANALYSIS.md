# PDF ファイルサイズ分析と最適化

## 観察された現象

**入力**: 2.28 MB（534ページ）
**出力**: 30.54 MB（4ページ目まで）
**増加比**: **13.4倍**

```
入力ファイル: odb_spec_user.pdf
  - ファイルサイズ: 2.28 MB
  - ページ数: 534
  - ページあたり平均: 4.5 KB

出力ファイル（個別ページ）: 000001.pdf ～ 000004.pdf
  - ページ 1: 10.05 MB
  - ページ 2: 5.12 MB
  - ページ 3: 5.12 MB
  - ページ 4: 5.12 MB
  - 平均/ページ: 6.11 MB
```

## 根本原因

### 1. 日本語フォントの埋め込み

PDFMathTranslate は日本語翻訳時に以下のフォントを埋め込んでいます：

```
- SourceHanSerifJP-Regular  (複数MB)
- SourceHanSerifJP-Bold     (複数MB)
- SiemensSans-Black         (元のドキュメント用)
```

**東アジア言語フォント（CJK フォント）は非常に大きい理由:**
- 漢字・ひらがな・カタカナなど数千の字形を含む
- 各ページに独立した PDF として出力されるため、各ページに全フォント埋め込み
- SourceHanSerifJP 単体で 6-8 MB

### 2. ページごとの独立した PDF 生成

```
元のPDF: 1 つの統合ファイル（フォント共有）
  - 534 ページ × フォントセット共有 = 2.28 MB

出力: 各ページが独立した PDF
  - ページ 1: フォントセット完全埋め込み ≈ 10 MB
  - ページ 2-4: フォントセット完全埋め込み ≈ 5 MB/page
  - ページ ごとに繰り返し = 30+ MB
```

## PDFMathTranslate の出力プロセス

```
入力 PDF (534ページ)
    ↓
1. ページごとに抽出
    ↓
2. LLM で翻訳（Qwen3 8B via Ollama）
    ↓
3. 翻訳済みテキストをページに配置
    ↓
4. 各ページを独立した PDF として出力 ← ここで全フォント埋め込み
    ↓
出力: pages/000001.pdf, pages/000002.pdf, ...
```

## 最適化オプション

### 1. フォント埋め込みを最小化

```python
# translator/__init__.py で設定可能
TranslationSettings(
    # 埋め込みフォントを指定（デフォルトはすべて埋め込み）
    primary_font_family="serif",  # serif, sans-serif, script から選択
    # または
    primary_font_family=None,  # システムフォント使用
)
```

**効果**: ページあたり 1-2 MB に削減される可能性

### 2. PDF 圧縮

PDFMathTranslate が出力後に圧縮できる場合：

```python
PDFSettings(
    # 画像圧縮
    image_quality=0.7,  # 0-1.0 (低いほど圧縮)
    # テキスト圧縮
    compress_streams=True,
)
```

### 3. 出力後の圧縮処理

```bash
# Ghostscript で再圧縮
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=compressed.pdf input.pdf
```

## 技術的な説明

### なぜ最初のページだけ 10 MB なのか？

**ページ 1 (10.05 MB)**:
- 元のドキュメントから抽出したすべてのリソース（画像、フォント）
- 翻訳テキスト
- 日本語フォント（SourceHanSerifJP）完全埋め込み

**ページ 2-4 (5.12-5.13 MB)**:
- 翻訳テキストのみ
- 日本語フォント（SourceHanSerifJP）完全埋め込み
- リソース数が少ない

### なぜ 534 ページすべてではなく 4 ページだけ出力？

```bash
$ cat _data/odbpp_translatol/output/job/log.txt | tail -20
...
Job Status: running
Current Page: 5
...
```

ジョブが実行中（ページ5で処理中）なため、ページ 1-4 のみ出力されています。

## 最適化への提案

### 短期的な解決策

1. **出力ファイルを統合する**
   - 各ページの PDF を 1 つのファイルにマージ
   - フォントを 1 回だけ埋め込み
   - **効果**: 30 MB → 15 MB 程度に削減（約 50%）

```python
# 実装例
from PyPDF2 import PdfMerger

merger = PdfMerger()
for page_pdf in sorted(Path('pages').glob('*.pdf')):
    merger.append(page_pdf)
merger.write('output.pdf')
```

2. **圧縮フォントを使用**
   - `primary_font_family="serif"` で埋め込みフォント削減
   - **効果**: ページあたり 10 MB → 2-3 MB（約 70% 削減）

### 中期的な解決策

1. **PDFMathTranslate 設定の最適化**
   - `skip_clean=False` で不要なリソース削除
   - 画像解像度削減オプション
   - フォント圧縮オプション

2. **出力後の処理**
   - Ghostscript での PDF 再圧縮
   - 画像品質の最適化

## 参考: 設定済みオプション

現在の `translator/__init__.py`:

```python
TranslationSettings(
    lang_in="en",
    lang_out="ja",
    output=str(output_dir),
    qps=4,
    pool_max_workers=2,
    custom_system_prompt="/no_think",
    no_auto_extract_glossary=True,
    min_text_length=10,
    # ← primary_font_family を追加可能
),
pdf=PDFSettings(
    no_dual=True,                          # 2段階翻訳を無効化
    skip_clean=True,                       # リソース削除を無効化（バグ防止）
    disable_rich_text_translate=True,      # リッチテキスト翻訳無効化
),
```

## 結論

**出力ファイルが大きい理由**: 
- 日本語フォント（SourceHanSerifJP）が各ページに完全埋め込み
- ページごとの独立した PDF として出力

**改善方法**:
1. フォント埋め込みオプションの最適化
2. 出力 PDF の統合と再圧縮
3. 両方で **70-90% の削減** が理論的に可能

**実装優先度**:
1. 🔴 高: `primary_font_family` 設定を追加
2. 🟡 中: 出力 PDF 統合処理
3. 🟢 低: 高度な圧縮最適化
