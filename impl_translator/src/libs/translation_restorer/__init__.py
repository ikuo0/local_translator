"""Restore translated text back into HTML."""

import json
from pathlib import Path

from bs4 import BeautifulSoup


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
                          Format: {"tag_000000": "翻訳済みテキスト", ...}
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
        translations = json.load(f)

    # Restore translations
    for tag in soup.find_all(True):
        if tag.name and tag.get("id"):
            tag_id = tag.get("id")

            if tag_id in translations:
                translated_text = translations[tag_id]
                # Clear existing content and set translated text
                tag.clear()
                tag.string = translated_text

    # Write output
    output_html.write_text(str(soup), encoding="utf-8")

    return output_html


def load_translations_from_text(text_content: str) -> dict:
    """
    Parse translated text in format: {ID=tag_XXXXXX} {text}

    Args:
        text_content: Text content with format {ID=...} {translated text}

    Returns:
        Dict: {"tag_000000": "翻訳済みテキスト", ...}

    Raises:
        ValueError: If format is invalid
    """
    translations = {}

    for line in text_content.strip().split("\n"):
        if not line.strip():
            continue

        if not line.startswith("{ID="):
            raise ValueError(f"Invalid translation format: {line}")

        # Extract ID and text
        end_id_pos = line.find("}")
        if end_id_pos == -1:
            raise ValueError(f"Invalid translation format: {line}")

        tag_id = line[4:end_id_pos]
        text = line[end_id_pos + 2:] if end_id_pos + 2 < len(line) else ""

        translations[tag_id] = text

    return translations
