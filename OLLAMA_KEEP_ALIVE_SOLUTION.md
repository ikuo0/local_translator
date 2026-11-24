# Ollama keep_alive=0 解決方法

## 問題
- Ollama のネイティブAPI では、リクエスト内の `keep_alive` パラメータが環境変数を上書きする
- pdf2zh_next 内部で Ollama クライアントを初期化されるため、直接的な制御が困難

## 採用した解決方法：OpenAI互換API への切り替え

### 仕組み
1. **Ollama は OpenAI互換API (`/v1` エンドポイント)を提供**
2. **OpenAI標準APIに `keep_alive` パラメータがない**
3. **結果として、Ollama の環境変数 `OLLAMA_KEEP_ALIVE: "0"` が有効になる**

### 実装変更

#### 1. docker-compose.yml
```yaml
ollama:
  environment:
    OLLAMA_KEEP_ALIVE: "0"  # 以前: "-1"
```

#### 2. impl_translator/src/libs/translator/__init__.py
```python
# 変更前
from pdf2zh_next.config.translate_engine_model import OllamaSettings
translate_engine_settings=OllamaSettings(ollama_host=host, ollama_model=model)

# 変更後
from pdf2zh_next.config.translate_engine_model import OpenAISettings
translate_engine_settings=OpenAISettings(
    openai_base_url=f"{host}/v1",
    openai_model=model,
    openai_api_key="dummy",  # Ollama ではAPIキー不要
)
```

### 効果
- **各リクエスト後、Ollama が即座にGPUメモリを解放**
- **メモリ蓄積によるハング/デッドロック の防止**
- **元のパッチ方式より確実で保守性が高い**

### 検証方法
```bash
watch -n 1 'docker compose exec -T ollama ollama ps'
# 翻訳リクエスト完了後、モデルが unload されることを確認
```

---

## 参考：他の解決方法との比較

| 方法 | OSS改変 | 追加実装 | 解放単位 | 確実性 |
|------|--------|-------|--------|--------|
| **OpenAI互換API（採用）** | 不要 | 最小限 | リクエスト単位 | ⭐⭐⭐⭐⭐ |
| Ollama パッチ | 不要 | 中程度 | リクエスト単位 | ⭐⭐⭐ |
| ページ単位アンロード | 不要 | 数行 | ページ単位 | ⭐⭐⭐⭐ |
| OSS 直接修正 | 必要 | 数行 | リクエスト単位 | ⭐⭐⭐⭐ |
