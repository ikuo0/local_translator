HTMLからPDFに変換するのであれば、**Noto Sans JP（ゴシック体）を基本フォントとして採用することを推奨します。**

Notoフォントは日本語の収録文字数が多く、ライセンス上も扱いやすいため、LinuxのDevContainer内でPDFを生成する用途に適しています。

## **推奨フォント**

| フォント                | 用途           | 優先度 |
| ------------------- | ------------ | --- |
| Noto Sans JP        | 本文・見出し・表     | 必須  |
| Noto Sans Mono      | コード・データ形式・座標 | 推奨  |
| Noto Serif JP       | 明朝体の文章       | 任意  |
| Noto Sans Symbols 2 | 特殊記号         | 任意  |
| Noto Sans Math      | 数学記号         | 任意  |

ODB++仕様書のような技術文書なら、基本的には **Noto Sans JPとNoto Sans Monoの2種類**で十分だと思います。

## **DevContainerへのインストール**

Debian・Ubuntu系のLinuxであれば、個別にフォントファイルをダウンロードする必要はありません。aptで導入できます。

Dockerfileに以下を追加してください。

```
RUN apt-get update && apt-get install -y \
    fontconfig \
    fonts-noto-cjk \
    fonts-noto-mono \
    fonts-noto-core \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*
```

`fonts-noto-cjk` には以下の日本語フォントが含まれています。

[image](https://www.google.com/s2/favicons?domain=https://packages.debian.org\&sz=32)

packages.debian.org+1



| フォント名                 | 種類     |
| --------------------- | ------ |
| Noto Sans CJK JP      | ゴシック体  |
| Noto Serif CJK JP     | 明朝体    |
| Noto Sans Mono CJK JP | 等幅フォント |

インストール確認：

```
fc-list :lang=ja
```

フォントの名前解決確認：

```
fc-match "Noto Sans CJK JP"
```

## **HTML側の共通CSS**

```
body {
    font-family: "Noto Sans CJK JP", "Meiryo", sans-serif;
    font-size: 11pt;
    line-height: 1.5;
}

pre, code {
    font-family: "Noto Sans Mono CJK JP", monospace;
    font-size: 10pt;
}

table {
    border-collapse: collapse;
    width: 100%;
}

th, td {
    border: 1px solid #999;
    padding: 4px 8px;
    overflow-wrap: anywhere;
}

@page {
    size: A4;
    margin: 15mm;
}
```

HTML閲覧時はWindowsの代替フォントも利用でき、LinuxでのPDF生成時はNotoフォントが使用されます。

## **PDF生成ライブラリ**

| ライブラリ                | 特徴                |
| -------------------- | ----------------- |
| Playwright（Chromium） | ブラウザと同じ描画結果をPDF化  |
| WeasyPrint           | 印刷向けCSSや改ページ制御に強い |

どちらも通常、PDF生成時にフォントをサブセット化して埋め込むため、今回の `pdf2zh_next` のような容量肥大化を抑えられます。

今回の構成なら、以下の役割分担がよいでしょう。

```
Docling         : PDF構造解析
BeautifulSoup   : HTML編集
Ollama          : 翻訳
Noto            : フォント
CSS             : レイアウト管理
Playwright      : PDF生成
```

**フォントはプロジェクト内で個別管理せず、DockerfileでOSにインストールする方式を推奨します。** DevContainerを再構築しても同じフォント環境を再現でき、完全オフラインでPDF生成が可能になります。