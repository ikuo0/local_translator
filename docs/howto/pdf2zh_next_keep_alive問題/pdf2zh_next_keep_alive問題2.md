可能です。ただし、Ollamaには**モデルをVRAMに残したまま、推論用キャッシュ（KVキャッシュ）だけを外部から明示的に削除する**ための公開APIは、私の把握している範囲ではありません。

モデルごとアンロードすることで、モデルが保持している推論用キャッシュも解放できます。

## **外部からキャッシュを解放する方法**

Ollamaに空のリクエストを送信します。

```
curl -X POST http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","keep_alive":0}'
```

これは翻訳リクエストとは独立した操作なので、`pdf2zh_next` のソースコードを変更する必要はありません。

正常に処理されると、以下のような応答が返ります。

```
{
    "model": "qwen3:8b",
    "response": "",
    "done": true,
    "done_reason": "unload"
}
```

これはOllamaの公式APIでサポートされている操作です。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## **Pythonから実行する場合**

```
import requestsresponse = requests.post(    "http://ollama:11434/api/generate",    json={        "model": "qwen3:8b",        "keep_alive": 0,    },    timeout=30,)response.raise_for_status()
```

## **解放されるもの・されないもの**

| 対象                   | 解放されるか |
| -------------------- | ------ |
| GPU上のモデルの重み          | 解放される  |
| KVキャッシュ              | 解放される  |
| モデルの推論用メモリ           | 解放される  |
| ダウンロード済みモデルファイル      | 維持される  |
| Ollamaサーバープロセス       | 維持される  |
| pdf2zh_next側の翻訳キャッシュ | 維持される  |

## **今回のPDF翻訳への適用**

現在の1ページずつ翻訳する構成なら、以下の処理で十分だと思います。

```
ページ翻訳
  ↓
PDF保存
  ↓
OllamaアンロードAPI実行
  ↓
次ページ翻訳
  ↓
Ollamaが自動的にモデルをロード
```

`pdf2zh_next` が内部で `keep_alive` を指定していても関係ありません。翻訳完了後に外部からアンロードを指示できるためです。

ただし、既にデッドロックが発生している状態では、アンロード要求自体が処理されない可能性があります。

**ハングアップの予防としてページ完了ごとにアンロードし、解消できなければコンテナを再起動する**という二段構えがよいでしょう。