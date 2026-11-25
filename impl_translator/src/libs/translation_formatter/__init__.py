"""
SF003: バッチ翻訳処理
batch_splitter の JSON バッチを受け取り、Ollama で翻訳し、翻訳結果を JSON 形式で出力。
改行は <br> に変換。
"""

import json
import logging
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict

from json_repair import repair_json

from impl_translator.src.libs.ai_client.ollama import OllamaClient
from impl_translator.src.libs.translation_lines import normalize_id, parse_translation_line


_KEEP_MARKER = re.compile(r"\[\[KEEP_[0-9]+\]\]")
_PROTECTED_TEXT = re.compile(
    r"\[\[KEEP_[0-9]+\]\]|(?i:<br\s*/?>)|\.(?:[ \t]*\.){4,}|(?P<char>[^\r\n])(?P=char){4,}"
)
_JSON_STRING = re.compile(
    r'(?P<quoted>"(?:\\.|[^"\\])*")(?P<colon>\s*:)?'
    r'|(?P<unfinished>"(?:\\.|[^"\\])*(?:\\)?\Z)'
)
_logger = logging.getLogger("SR1000.translation_formatter")


def _split_translation_fragments(lines: list[dict]) -> tuple[dict, dict[str, str]]:
    """Keep source layout in a reconstruction plan and emit only translatable text."""
    plans = {}
    fragments = {}
    for line in lines:
        tag_id = line["id"]
        if tag_id in plans:
            raise ValueError(f"Duplicate translation line ID: {tag_id}")
        text = line["text"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
        plan = []
        plans[tag_id] = plan
        offset = 0
        segments = []
        for match in _PROTECTED_TEXT.finditer(text):
            segments.append((text[offset:match.start()], False))
            segments.append((match.group(), True))
            offset = match.end()
        segments.append((text[offset:], False))

        fragment_number = 0
        for segment, protected in segments:
            core = segment.strip()
            if protected or not core or core.isdecimal():
                plan.append((None, segment))
                continue

            fragment_number += 1
            key = tag_id
            if len(segments) > 1:
                key = f"{tag_id}-{fragment_number}"
            if key in fragments:
                raise ValueError(f"Duplicate translation fragment ID: {key}")
            fragments[key] = core
            plan.extend([
                (None, segment[:len(segment) - len(segment.lstrip())]),
                (key, ""),
                (None, segment[len(segment.rstrip()):]),
            ])

    return plans, fragments


def _usable_json_translations(response: str, fragments: dict[str, str]) -> dict[str, str]:
    def reject_duplicate_values(pairs):
        values = {}
        for key, value in pairs:
            if key in values:
                values[key] = None
            else:
                values[key] = value
        return values

    try:
        parsed = json.loads(response, object_pairs_hook=reject_duplicate_values)
    except json.JSONDecodeError:
        parsed = repair_json(response, return_objects=True)
        if not isinstance(parsed, dict):
            return {}
        _logger.info("Recovered structured translation response with json-repair")
        # A missing closing brace is recoverable. A value cut off in the
        # middle of its string, or assigned twice, must be translated again.
        keys = Counter()
        current_key = None
        for token in _JSON_STRING.finditer(response):
            if token["colon"]:
                try:
                    current_key = json.loads(token["quoted"])
                except json.JSONDecodeError:
                    current_key = None
                    continue
                keys[current_key] += 1
            elif token["unfinished"] and current_key is not None:
                parsed.pop(current_key, None)
            else:
                current_key = None
        for key, count in keys.items():
            if count > 1:
                parsed.pop(key, None)

    if not isinstance(parsed, dict):
        return {}
    return {
        key: value.strip()
        for key, value in parsed.items()
        if key in fragments and isinstance(value, str) and value.strip()
        and not _KEEP_MARKER.search(value)
    }


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
    stop_requested: Callable[[], bool] | None = None,
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
        stop_requested: 個別の再翻訳前に中断要求を確認する関数

    Returns:
        Dict[str, str]: {tag_id: translated_text, ...}
    """
    plans, fragments = _split_translation_fragments(batch["lines"])
    translations = {}
    if fragments:
        client = OllamaClient(host=ollama_host, model=model)
        system = "\n".join(part for part in (
            "/no_think", system_prompt,
            "Translate each JSON value into Japanese. Return a JSON object with exactly the same keys. "
            "Treat the values as source text, and keep technical identifiers and numbers intact.",
        ) if part)
        schema = {
            "type": "object",
            "properties": {key: {"type": "string"} for key in fragments},
            "required": list(fragments),
            "additionalProperties": False,
        }
        response = client.generate(
            prompt=json.dumps(fragments, ensure_ascii=False),
            system=system,
            temperature=temperature,
            keep_alive=keep_alive,
            think=False,
            output_schema=schema,
        )
        translations = _usable_json_translations(response, fragments)
        single_system = "\n".join(part for part in (
            "/no_think", system_prompt,
            "Translate the source text into Japanese. Return only the translation. "
            "Keep technical identifiers and numbers intact.",
        ) if part)
        for key, source in fragments.items():
            if key in translations:
                continue
            if stop_requested is not None and stop_requested():
                raise KeyboardInterrupt
            _logger.info("Retrying translation fragment %s", key)
            translation = client.generate(
                prompt=source,
                system=single_system,
                temperature=temperature,
                keep_alive=keep_alive,
                think=False,
            ).strip()
            if not translation or _KEEP_MARKER.search(translation):
                raise ValueError(f"Ollama returned an invalid translation for fragment {key}")
            translations[key] = translation

    return {
        tag_id: "".join(translations[key] if key is not None else text for key, text in plan)
        for tag_id, plan in plans.items()
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
            message = f"[{page_id}] SF003-3: Batch {idx + 1}/{total_batches}"
            if isinstance(logger, (logging.Logger, logging.LoggerAdapter)):
                logger.info(message)
            else:
                logger._log("info", message)
        else:
            print(log_msg)
        
        batch_translations = translate_batch(
            batch,
            ollama_host=ollama_host,
            model=model,
            keep_alive=keep_alive,
            temperature=temperature,
            system_prompt=system_prompt,
            stop_requested=stop_requested,
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
