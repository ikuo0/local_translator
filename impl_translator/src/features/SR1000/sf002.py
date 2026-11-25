"""SF002: Prepare source HTML for translation."""

from pathlib import Path

from impl_translator.src.libs.html_preproc import preprocess_html


def prepare_html(input_html: Path, output_dir: Path) -> Path:
    """Preprocess the source and return the path to preproc.html."""
    return preprocess_html(input_html=input_html, output_html=output_dir / "preproc.html")
