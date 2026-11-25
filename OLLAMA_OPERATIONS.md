# Ollama の運用・API 診断

初回セットアップは [README](README.md#1-ollama-のセットアップと起動) を参照してください。

## WSL コンソールでのコンテナ管理

起動時やメンテナンス時に、WSL コンソールでリポジトリのルートから実行します。

```bash
docker compose exec ollama nvidia-smi
docker compose exec ollama ollama pull qwen3:8b
docker compose exec ollama ollama run qwen3:8b
docker compose exec ollama ollama ps
docker compose logs --tail=20 ollama
```

コンテナの再起動は `docker compose restart ollama` で行います。`docker-compose.yml` の環境変数を変更した場合は、ジョブ終了後に `docker compose up -d ollama` で設定を反映します。全サービスを停止する `docker compose down` は Dev Container も停止します。

## Dev Container での API 確認

```bash
curl -fsS http://ollama:11434/api/ps | python -m json.tool
curl -fsS http://ollama:11434/api/version
```

同じプロンプトを2回送り、Ollama が返す入力トークン数とキャッシュ件数を比較できます。この例ではモデルの保持時間を30分に指定します。

```bash
set -o pipefail
for run in 1 2; do
  curl -fsS http://ollama:11434/api/generate \
    -H 'Content-Type: application/json' \
    -d '{"model":"qwen3:8b","prompt":"Hello","stream":false,"think":false,"keep_alive":"30m"}' \
    | python -c 'import json,sys; d=json.load(sys.stdin); print({k: d.get(k) for k in ("prompt_eval_cached_count", "prompt_eval_count")})'
done
```

### 翻訳ジョブのキャッシュ診断

`sr1000_main` に `--debug-ollama-cache` を追加すると、翻訳前に `Hello` を `keep_alive: "0"` で送り、`prompt_eval_cached_count` と `prompt_eval_count` をジョブログに記録します。このリクエストのキャッシュ表示は、`cache=not_used` がキャッシュ件数0、`cache=used` が1以上、`cache=unknown` が有効な件数を取得できなかったことを示します。

翻訳の通常リクエストでは `keep_alive` の既定値は `5m` です。モデルの保持時間に関する設計メモは [Ollama Keep Alive](OLLAMA_KEEP_ALIVE_SOLUTION.md) を参照してください。

## Ollama クライアント

CLI の `--host` と `--model` はサブコマンドの前に指定します。

```bash
python -m impl_translator.src.libs.ai_client --host http://ollama:11434 --model qwen3:8b \
  generate --prompt 'Translate into Japanese: Hello world' --temperature 0.7 --keep-alive 5m
python -m impl_translator.src.libs.ai_client --host http://ollama:11434 \
  chat --message 'What is 2 + 2?'
python -m impl_translator.src.libs.ai_client --host http://ollama:11434 list-models
python -m impl_translator.src.libs.ai_client --host http://ollama:11434 model-info
python -m impl_translator.src.libs.ai_client --host http://ollama:11434 unload
```

Python からは `OllamaClient` を利用できます。`chat` はロールと本文を持つメッセージのリストを受け取り、`get_model_info()`、`list_models()`、`unload_model()` はそれぞれモデルの情報取得、一覧取得、アンロードを行います。

```python
from impl_translator.src.libs.ai_client import OllamaClient

client = OllamaClient(host="http://ollama:11434", model="qwen3:8b", timeout=300)
print(client.generate("Translate into Japanese: Hello world", keep_alive="5m"))
```
