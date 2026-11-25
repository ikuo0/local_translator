"""SF003: Extract, batch, and translate the text of an HTML page."""

import json
import logging
from contextlib import AbstractContextManager
from pathlib import Path
from threading import Event

from impl_translator.src.libs.batch_splitter import split_text_into_batches
from impl_translator.src.libs.html_text_extractor import extract_tag_text, format_as_text_lines
from impl_translator.src.libs.translation_formatter import translate_batches


def translate_page(
    input_html: Path,
    output_dir: Path,
    *,
    page_id: str,
    ollama_host: str,
    model: str,
    temperature: float,
    system_prompt: str | None,
    logger: logging.Logger,
    ollama_lock: AbstractContextManager[object],
    stop_requested: Event,
) -> Path:
    """Translate a prepared page and return the path to translations.json."""
    lines = extract_tag_text(input_html)
    text_file = output_dir / "extracted.txt"
    text_file.write_text(format_as_text_lines(lines), encoding="utf-8")
    logger.info("[%s] SF003-1: Extracted %d tags", page_id, len(lines))

    batches = split_text_into_batches(text_file, max_chars=1500)
    batches_file = output_dir / "batches.json"
    batches_file.write_text(json.dumps(batches, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[%s] SF003-2: Split into %d batches", page_id, len(batches))

    translations_file = output_dir / "translations.json"
    logger.info("[%s] SF003-3: Translating %d batches...", page_id, len(batches))
    with ollama_lock:
        if stop_requested.is_set():
            raise KeyboardInterrupt
        translate_batches(
            input_batches_json=batches_file,
            output_translations_json=translations_file,
            ollama_host=ollama_host,
            model=model,
            temperature=temperature,
            page_id=page_id,
            logger=logger,
            stop_requested=stop_requested.is_set,
            system_prompt=system_prompt,
        )
    logger.info("[%s] SF003-3: All %d batches translated", page_id, len(batches))
    return translations_file
