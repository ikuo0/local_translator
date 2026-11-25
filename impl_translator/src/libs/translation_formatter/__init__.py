"""
SF003: バッチ翻訳処理
batch_splitter の JSON バッチを受け取り、Ollama で翻訳し、翻訳結果を JSON 形式で出力。
改行は <br> に変換。
"""

import json
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict

from impl_translator.src.libs.ai_client.ollama import OllamaClient
from impl_translator.src.libs.translation_lines import normalize_id, parse_translation_line


_KEEP_MARKER = re.compile(r"\[\[KEEP_[0-9]+\]\]")
_REPEATED_TEXT = re.compile(r"\[\[KEEP_[0-9]+\]\]|\.(?:[ \t]*\.){4,}|(?P<char>[^\r\n])(?P=char){4,}")


def _protect_repeated_text(prompt: str) -> tuple[str, dict[str, dict[str, str]]]:
    reserved = set(_KEEP_MARKER.findall(prompt))
    protected_by_id = {}
    protected_lines = []
    keep_counter = 0
    for line in prompt.split("\n"):
        tag_id, separator, text = line.partition(" ")
        replacements = {}

        def protect(match: re.Match[str]) -> str:
            nonlocal keep_counter
            while True:
                keep_counter += 1
                marker = f"[[KEEP_{keep_counter}]]"
                if marker not in reserved:
                    break
            replacements[marker] = match.group()
            return marker

        protected_lines.append(tag_id + separator + _REPEATED_TEXT.sub(protect, text))
        if replacements:
            protected_by_id[tag_id] = replacements

    return "\n".join(protected_lines), protected_by_id


def format_batch_for_prompt(batch: Dict[str, Any]) -> str:
    """
    バッチを Ollama API 送信用のテキスト形式に変換。

    入力: batch_splitter の出力形式
    {
        "batch_id": 0,
        "lines": [
            {"id": "id000000", "text": "..."},
            {"id": "id000001", "text": "..."}
        ],
        "char_count": 1234
    }

    出力: Ollama 送信用テキスト
    id000000 テキスト
    id000001 テキスト

    Returns:
        str: Ollama API に送信するテキスト
    """
    lines_text = []
    for line in batch["lines"]:
        tag_id = normalize_id(line["id"])
        text = line["text"]
        # 改行を <br> に変換
        text = text.replace("\n", "<br>")
        lines_text.append(f"{tag_id} {text}")

    return "\n".join(lines_text)


def parse_translation_response(response_text: str) -> Dict[str, str]:
    """
    Ollama の翻訳応答を解析し、ID -> 翻訳テキストのマッピングを返す。

    入力: Ollama の応答テキスト
    id000000 翻訳済みテキスト
    id000001 別の翻訳済みテキスト

    Returns:
        Dict[str, str]: {tag_id: translated_text, ...}
    """
    result = {}
    for line in response_text.splitlines():
        parsed = parse_translation_line(line)
        if parsed is not None:
            tag_id, text = parsed
            result[tag_id] = text

    return result


def translate_batch(
    batch: Dict[str, Any],
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    keep_alive: str = "5m",
    temperature: float = 0.3,
    system_prompt: str | None = None,
) -> Dict[str, str]:
    """
    1 つのバッチを翻訳。

    Args:
        batch: batch_splitter の出力形式
        ollama_host: Ollama のホスト URL
        model: 使用モデル名
        keep_alive: Ollama のモデルメモリ保持時間
        temperature: 翻訳の創意性（通常は低め）
        system_prompt: 翻訳分野などの補足情報

    Returns:
        Dict[str, str]: {tag_id: translated_text, ...}
    """
    # バッチを Ollama 送信用フォーマットに変換
    prompt_text, protected_by_id = _protect_repeated_text(format_batch_for_prompt(batch))

    # Ollama クライアント初期化
    client = OllamaClient(host=ollama_host, model=model)

    # 翻訳プロンプト作成
    instructions = (
        "Translate the text after the ID on each line into Japanese. "
        "Copy the ID (for example id000006) exactly, followed by a space and the translation. "
        "Return one line per input line in the same order. Preserve <br> markers."
    )
    if protected_by_id:
        instructions += " Copy each [[KEEP_n]] marker exactly once on its original ID line."
    system = "\n".join(part for part in ("/no_think", system_prompt, instructions) if part)

    # API 呼び出し
    response = client.generate(
        prompt=prompt_text,
        system=system,
        temperature=temperature,
        keep_alive=keep_alive,
        think=False,
    )

    # 応答をパース
    translations = {
        normalize_id(tag_id): text
        for tag_id, text in parse_translation_response(response).items()
    }
    if protected_by_id:
        for tag_id in translations.keys() | protected_by_id.keys():
            text = translations.get(tag_id, "")
            replacements = protected_by_id.get(tag_id, {})
            if Counter(_KEEP_MARKER.findall(text)) != Counter(replacements.keys()):
                raise ValueError(f"Ollama response has missing or unexpected KEEP markers for {tag_id}")
            if replacements:
                translations[tag_id] = _KEEP_MARKER.sub(
                    lambda match: replacements[match.group()], text
                )
    original_ids = {normalize_id(line["id"]): line["id"] for line in batch["lines"]}
    return {
        original_ids[tag_id]: text
        for tag_id, text in translations.items()
        if tag_id in original_ids
    }


def translate_batches(
    input_batches_json: Path,
    output_translations_json: Path,
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    keep_alive: str = "5m",
    temperature: float = 0.3,
    page_id: str = None,
    logger=None,
    stop_requested: Callable[[], bool] | None = None,
    system_prompt: str | None = None,
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
        stop_requested: バッチ間で中断要求を確認する関数（オプション）
        system_prompt: 各バッチに追加する翻訳の補足情報

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
        if stop_requested is not None and stop_requested():
            raise KeyboardInterrupt
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
            system_prompt=system_prompt,
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
