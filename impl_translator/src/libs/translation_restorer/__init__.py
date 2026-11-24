"""Restore translated text back into HTML."""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from impl_translator.src.libs.html_text_extractor import direct_text_nodes, iter_translatable_tags
from impl_translator.src.libs.translation_lines import normalize_id, parse_translation_line


def restore_translations_to_html(
    input_html: Path,
    translations_json: Path,
    output_html: Path,
) -> Path:
    """
    Restore translated text back into HTML using ID mapping.

    Args:
        input_html: Path to preprocessed HTML file (with IDs)
        translations_json: Path to JSON file with translations
                          Format: {"id000000": "翻訳済みテキスト", ...}
        output_html: Path to output HTML file

    Returns:
        Path to the generated HTML file

    Raises:
        FileNotFoundError: If input files do not exist
        ValueError: If format is invalid
    """
    input_html = input_html.resolve()
    translations_json = translations_json.resolve()
    output_html = output_html.resolve()

    if not input_html.exists():
        raise FileNotFoundError(f"HTML file not found: {input_html}")

    if not translations_json.exists():
        raise FileNotFoundError(f"Translations file not found: {translations_json}")

    output_html.parent.mkdir(parents=True, exist_ok=True)

    # Load HTML
    html_content = input_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    # Load translations
    with open(translations_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    translations = data.get("translations", data)

    for tag in iter_translatable_tags(soup):
        tag_id = tag["id"]
        translated_text = translations.get(tag_id, translations.get(normalize_id(tag_id)))
        nodes = direct_text_nodes(tag)
        if translated_text is not None and nodes:
            first, *remaining = nodes
            leading = first[:len(first) - len(first.lstrip())]
            trailing = first[len(first.rstrip()):]
            first.replace_with(f"{leading}{translated_text}{trailing}")
            for node in remaining:
                node.extract()

    # Write output
    output_html.write_text(str(soup), encoding="utf-8")

    return output_html


def load_translations_from_text(text_content: str) -> dict:
    """
    Parse translated text in format: idXXXXXX {text}

    Args:
        text_content: Text content with format id000006 followed by translated text

    Returns:
        Dict: {"id000000": "翻訳済みテキスト", ...}

    Raises:
        ValueError: If format is invalid
    """
    translations = {}

    for line in text_content.strip().split("\n"):
        if not line.strip():
            continue

        parsed = parse_translation_line(line)
        if parsed is None:
            raise ValueError(f"Invalid translation format: {line}")
        tag_id, text = parsed

        translations[tag_id] = text

    return translations
