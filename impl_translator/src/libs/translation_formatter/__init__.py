"""
SF003: バッチ翻訳処理
batch_splitter の JSON バッチを受け取り、Ollama で翻訳し、翻訳結果を JSON 形式で出力。
改行は <br> に変換。
"""

import json
from pathlib import Path
from typing import Any, Dict

from impl_translator.src.libs.ai_client.ollama import OllamaClient


def format_batch_for_prompt(batch: Dict[str, Any]) -> str:
    """
    バッチを Ollama API 送信用のテキスト形式に変換。

    入力: batch_splitter の出力形式
    {
        "batch_id": 0,
        "lines": [
            {"id": "tag_000000", "text": "..."},
            {"id": "tag_000001", "text": "..."}
        ],
        "char_count": 1234
    }

    出力: Ollama 送信用テキスト
    {ID=tag_000000} テキスト
    {ID=tag_000001} テキスト

    Returns:
        str: Ollama API に送信するテキスト
    """
    lines_text = []
    for line in batch["lines"]:
        tag_id = line["id"]
        text = line["text"]
        # 改行を <br> に変換
        text = text.replace("\n", "<br>")
        lines_text.append(f"{{ID={tag_id}}} {text}")

    return "\n".join(lines_text)


def parse_translation_response(response_text: str) -> Dict[str, str]:
    """
    Ollama の翻訳応答を解析し、ID -> 翻訳テキストのマッピングを返す。

    入力: Ollama の応答テキスト
    {ID=tag_000000} 翻訳済みテキスト
    {ID=tag_000001} 別の翻訳済みテキスト

    Returns:
        Dict[str, str]: {tag_id: translated_text, ...}
    """
    result = {}
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # {ID=tag_XXXXXX} テキスト の形式をパース
        if line.startswith("{ID=") and "}" in line:
            end_bracket = line.index("}")
            tag_id = line[4:end_bracket]  # {ID= の後から } までを取得
            text = line[end_bracket + 1:].strip()
            # <br> は JSON に保存する時もそのまま（translation_restorer で処理）
            result[tag_id] = text
        else:
            # 形式が違う場合はスキップ
            pass

    return result


def translate_batch(
    batch: Dict[str, Any],
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    keep_alive: str = "5m",
    temperature: float = 0.3,
) -> Dict[str, str]:
    """
    1 つのバッチを翻訳。

    Args:
        batch: batch_splitter の出力形式
        ollama_host: Ollama のホスト URL
        model: 使用モデル名
        keep_alive: Ollama のモデルメモリ保持時間
        temperature: 翻訳の創意性（通常は低め）

    Returns:
        Dict[str, str]: {tag_id: translated_text, ...}
    """
    # バッチを Ollama 送信用フォーマットに変換
    prompt_text = format_batch_for_prompt(batch)

    # Ollama クライアント初期化
    client = OllamaClient(host=ollama_host, model=model)

    # 翻訳プロンプト作成
    system_prompt = "You are a professional translator. Translate the following text into Japanese. Keep the {ID=tag_XXXXXX} format intact in the output."

    # API 呼び出し
    response = client.generate(
        prompt=prompt_text,
        system=system_prompt,
        temperature=temperature,
        keep_alive=keep_alive,
    )

    # 応答をパース
    translations = parse_translation_response(response)

    return translations


def translate_batches(
    input_batches_json: Path,
    output_translations_json: Path,
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    keep_alive: str = "5m",
    temperature: float = 0.3,
    page_id: str = None,
    logger=None,
) -> Dict[str, Any]:
    """
    複数バッチを順次翻訳し、全翻訳結果を 1 つの JSON ファイルに保存。

    Args:
        input_batches_json: batch_splitter の出力ファイル
        output_translations_json: 翻訳結果の出力ファイル
        ollama_host: Ollama のホスト URL
        model: 使用モデル名
        keep_alive: Ollama のモデルメモリ保持時間
        temperature: 翻訳の創意性
        page_id: ログ出力用のページID（オプション）
        logger: ロガー（オプション）

    Returns:
        Dict[str, Any]: {
            "total_batches": int,
            "translations": {tag_id: translated_text, ...}
        }
    """
    # バッチを読み込み
    with open(input_batches_json, "r", encoding="utf-8") as f:
        batches = json.load(f)

    # 全翻訳結果を集約
    all_translations = {}
    total_batches = len(batches)

    for idx, batch in enumerate(batches):
        # 進捗表示
        log_msg = f"[{idx + 1}/{total_batches}] Batch {batch['batch_id']} を翻訳中..."
        if page_id and logger:
            logger._log("info", f"[{page_id}] SF003-3: Batch {idx + 1}/{total_batches}")
        else:
            print(log_msg)
        
        batch_translations = translate_batch(
            batch,
            ollama_host=ollama_host,
            model=model,
            keep_alive=keep_alive,
            temperature=temperature,
        )
        all_translations.update(batch_translations)

    # 結果を JSON で保存
    output_data = {
        "total_batches": total_batches,
        "translations": all_translations,
    }

    output_translations_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_translations_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    return output_data


def translate_batches_with_metadata(
    input_batches_json: Path,
    output_translations_json: Path,
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    keep_alive: str = "5m",
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    複数バッチを順次翻訳し、メタデータ付きで JSON ファイルに保存。

    Returns:
        Dict[str, Any]: {
            "metadata": {
                "model": str,
                "total_batches": int,
                "ollama_host": str
            },
            "translations": {tag_id: translated_text, ...}
        }
    """
    # バッチを読み込み
    with open(input_batches_json, "r", encoding="utf-8") as f:
        batches = json.load(f)

    # 全翻訳結果を集約
    all_translations = {}
    total_batches = len(batches)

    for idx, batch in enumerate(batches):
        print(f"[{idx + 1}/{total_batches}] Batch {batch['batch_id']} を翻訳中...")
        batch_translations = translate_batch(
            batch,
            ollama_host=ollama_host,
            model=model,
            keep_alive=keep_alive,
            temperature=temperature,
        )
        all_translations.update(batch_translations)

    # メタデータ付きで結果を JSON で保存
    output_data = {
        "metadata": {
            "model": model,
            "total_batches": total_batches,
            "ollama_host": ollama_host,
        },
        "translations": all_translations,
    }

    output_translations_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_translations_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    return output_data
