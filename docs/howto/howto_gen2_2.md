単純に `get_text()` でHTML全体のテキストを抽出してしまうと、その通りです。表の構造情報が失われるため、元に戻すことは困難です。

ただし、BeautifulSoupは**HTMLの構造を保持したまま、個々のテキスト要素を置換することができます。**

## **1. テキストノードの置換方式**

例えば、Doclingが以下のHTMLを生成したとします。

```
<table>
    <tr>
        <th>Parameter</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>WIDTH</td>
        <td>Width of the object</td>
    </tr>
</table>
```

BeautifulSoupで各テキストノードを取得し、翻訳結果で置換します。

```
from bs4 import BeautifulSoupsoup = BeautifulSoup(html, "html.parser")for node in soup.find_all(string=True):    if not node.strip():        continue    if node.find_parent(["style", "script", "pre", "code"]):        continue    translated = translate(node.strip())    node.replace_with(translated)result = str(soup)
```

`translate()` は自前で実装するOllama翻訳関数です。

結果：

```
<table>
    <tr>
        <th>パラメータ</th>
        <th>説明</th>
    </tr>
    <tr>
        <td>WIDTH</td>
        <td>オブジェクトの幅</td>
    </tr>
</table>
```

HTMLタグや属性を変更しないため、表構造、セル結合、リスト階層などはそのまま維持されます。

## **2. ただし、テキストノード単位の翻訳にも問題がある**

例えば以下のHTMLです。

```
<p>The <b>surface</b> must be closed.</p>
```

テキストノード単位では次の3つに分割されます。

```
The
surface
must be closed.
```

これらを個別に翻訳すると、文章として不自然になる可能性があります。

そのため、実際には段落やセルなど、意味のある単位で翻訳するほうが適しています。

## **3. 推奨する翻訳単位**

| HTML要素       | 翻訳単位     |
| ------------ | -------- |
| `p`          | 段落単位     |
| `td`         | セル単位     |
| `th`         | ヘッダーセル単位 |
| `li`         | リスト項目単位  |
| `h1` ～ `h6`  | 見出し単位    |
| `pre`、`code` | 原則翻訳しない  |
| `img`        | 変更しない    |

太字などのインラインタグが含まれる場合は、タグをプレースホルダー化して翻訳後に復元する方法もあります。

## **4. 複数要素をまとめてOllamaに渡す方式**

Ollamaへのリクエスト回数を削減するなら、抽出した文章にIDを割り当てて、一括翻訳する方法もあります。

入力：

```
{
    "001": "Parameter",
    "002": "Description",
    "003": "Width of the object",
    "004": "Height of the object"
}
```

LLM出力：

```
{
    "001": "パラメータ",
    "002": "説明",
    "003": "オブジェクトの幅",
    "004": "オブジェクトの高さ"
}
```

**Docling生成HTML**

表・リスト・見出し・画像

**BeautifulSoup**

翻訳対象の抽出・ID割り当て

**HTML構造**

そのまま保持

**Ollama翻訳**

ID付きテキスト群

**IDに基づく翻訳文の置換**

**翻訳済みHTML**

元の文書構造を維持

今回のQwen3 8Bによる翻訳では、このID付きJSON方式も有力だと思います。翻訳前後でIDの一致を検証すれば、翻訳漏れも機械的に検出できます。

**HTMLの再構築をAIに任せず、文字列の翻訳だけをAIに任せる**という設計です。表やリストの維持精度はLLMの性能に依存しなくなります。