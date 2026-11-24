"""Extract text from HTML on a per-tag basis."""

from pathlib import Path

from bs4 import BeautifulSoup


def extract_tag_text(input_html: Path) -> list[dict]:
    """
    Extract text from HTML on a per-tag basis.

    Returns list of dicts with tag ID and text content.

    Args:
        input_html: Path to preprocessed HTML file (with IDs)

    Returns:
        List of dicts: [{"id": "tag_000000", "text": "..."}, ...]

    Raises:
        FileNotFoundError: If input HTML does not exist
        ValueError: If HTML format is invalid
    """
    input_html = input_html.resolve()

    if not input_html.exists():
        raise FileNotFoundError(f"HTML file not found: {input_html}")

    html_content = input_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract text from all tags that have an id
    text_lines = []

    for tag in soup.find_all(True):  # True = find all tags
        if tag.name and tag.get("id"):
            tag_id = tag.get("id")
            # Get all text within this tag
            text_content = tag.get_text(strip=False)
            # Clean up excess whitespace but preserve structure
            text_content = " ".join(text_content.split())

            if text_content:  # Only include non-empty tags
                text_lines.append({
                    "id": tag_id,
                    "text": text_content,
                })

    return text_lines


def format_as_text_lines(text_lines: list[dict]) -> str:
    """
    Format extracted text as line-delimited text for processing.

    Args:
        text_lines: List of dicts from extract_tag_text()

    Returns:
        Formatted string: "{ID=tag_000000} {text}\n{ID=tag_000001} {text}\n..."
    """
    lines = []
    for item in text_lines:
        lines.append(f"{{ID={item['id']}}} {item['text']}")

    return "\n".join(lines)
