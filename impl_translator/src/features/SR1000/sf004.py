"""SF004: Restore translated text to HTML."""

from pathlib import Path

from impl_translator.src.libs.translation_restorer import restore_translations_to_html


def restore_page_html(input_html: Path, translations_json: Path, output_dir: Path) -> Path:
    """Restore translations and return the path to translated.html."""
    return restore_translations_to_html(
        input_html=input_html,
        translations_json=translations_json,
        output_html=output_dir / "translated.html",
    )
