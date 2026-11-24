**VRAM 8GBで十分実行可能です。** 過去に7Bモデルが動作していたのであれば、PDFの翻訳も問題なく実行できる可能性が高いです。

PDF一括翻訳といっても、PDF全体をLLMに入力するわけではありません。基本的には以下の処理になります。

1. PDFから文章とレイアウト情報を抽出
2. 段落などの単位で文章を分割
3. Ollamaに文章を渡して翻訳
4. 翻訳結果を元のレイアウトに配置
5. PDFとして再生成

そのため、PDFが数百ページあっても、必要なVRAMがページ数に比例して増えるわけではありません。主に処理時間が長くなります。

## **1. 使用するモデル**

翻訳用途なら、推論特化モデルよりも多言語対応の通常モデルが扱いやすいです。

| モデル            | モデル容量     | VRAM 8GBでの運用 |
| -------------- | --------- | ------------ |
| Qwen2.5 3B     | 1.9GB     | 余裕あり         |
| **Qwen2.5 7B** | **4.7GB** | **推奨**       |
| Qwen3 4B       | 2.5GB     | 余裕あり         |
| Qwen3 8B       | 5.2GB     | コンテキスト長に注意   |
| Qwen2.5 14B    | 9.0GB     | CPUとの併用が必要   |

容量はOllama公式の標準配布モデルの値です。実行時には別途KVキャッシュなどのメモリが必要になります。

[image](https://www.google.com/s2/favicons?domain=https://ollama.com\&sz=32)

Ollama+1



## **2. インストール方法**

Windows 11上でOllamaを動かし、PDFMathTranslate-nextをPython環境にインストールする構成が簡単です。

### **Ollama側**

```
ollama pull qwen2.5:7b
```

動作確認：

```
ollama run qwen2.5:7b
```

### **PDFMathTranslate-next側**

Pythonの仮想環境内で以下を実行します。

```
pip install pdf2zh-next
```

Web UIを起動します。

```
pdf2zh_next --gui
```

ブラウザ上でPDFを選択して翻訳できます。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## **3. 翻訳設定**

Web UIでは、まず以下の設定で試すとよいでしょう。

| 設定項目                | 設定値                      |
| ------------------- | ------------------------ |
| Translation Service | Ollama                   |
| Ollama Host         | `http://127.0.0.1:11434` |
| Ollama Model        | `qwen2.5:7b`             |
| Source Language     | `en`                     |
| Target Language     | `ja`                     |
| QPS                 | 1                        |
| 同時処理数（設定可能な場合）      | 1                        |
| コンテキスト長の目安          | 4096～8192                |

Docker内からホスト側のOllamaに接続する場合は、接続先の設定が異なります。

[公式セットアップマニュアル（日本語）](https://pdf2zh-next.com/ja/getting-started/USAGE_webui.html?utm_source=chatgpt.com)

## **4. 翻訳時間の目安**

RTX4060 8GBで7B量子化モデルを使用する場合の、仮の処理時間です。

1ページあたり500出力トークン、生成速度を毎秒20～40トークンと仮定します。

10ページ

2～4分

100ページ

21～42分

300ページ

63～125分

500ページ

104～208分

トークン生成時間のみの概算。PDF解析、プロンプト処理、再試行、レイアウト再構築の時間は別途必要です。

実際には数時間単位の処理になる可能性がありますが、一度翻訳すれば繰り返す必要はありません。

## **5. ODB++仕様書の翻訳で注意すること**

技術仕様書なので、カスタムプロンプトを設定できる場合は、以下のような指示を加えたほうがよいです。

```
Translate the technical specification into Japanese.

- Preserve all command names, identifiers, and file paths.
- Preserve all numerical values and units.
- Do not translate code or data format examples.
- Use consistent PCB and CAM terminology.
- Do not summarize or omit any information.
- Output only the translated text.
```

例えば `surface` や `features` は、説明文中では翻訳しても、ファイル名やデータ構造名として登場する場合は原文を維持する必要があります。

まずはODB++仕様書の10ページ程度を翻訳して、翻訳品質、処理速度、VRAM使用量を確認してから全ページを処理するのがよいでしょう。

手持ちのRTX4060であれば、翻訳のためにグラフィックボードを買い替える必要はないと思います。