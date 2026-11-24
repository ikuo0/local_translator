"""Extract text from HTML on a per-tag basis."""

from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

from impl_translator.src.libs.translation_lines import normalize_id


def iter_translatable_tags(soup: BeautifulSoup):
    """Yield IDs inside the body, or inside a standalone HTML fragment."""
    if soup.body is not None:
        tags = (soup.body, *soup.body.find_all(id=True))
    elif soup.html is None:
        tags = soup.find_all(id=True)
    else:
        return

    excluded = {"head", "title", "style", "script"}
    for tag in tags:
        if tag.get("id") and tag.name not in excluded:
            if not any(parent.name in excluded for parent in tag.parents):
                yield tag


def direct_text_nodes(tag: Tag) -> list[NavigableString]:
    """Return nonblank text directly owned by this element."""
    return [
        node for node in tag.children
        if type(node) is NavigableString and node.strip()
    ]


def extract_tag_text(input_html: Path) -> list[dict]:
    """
    Extract text from HTML on a per-tag basis.

    Returns list of dicts with tag ID and text content.

    Args:
        input_html: Path to preprocessed HTML file (with IDs)

    Returns:
        List of dicts: [{"id": "id000000", "text": "..."}, ...]

    Raises:
        FileNotFoundError: If input HTML does not exist
        ValueError: If HTML format is invalid
    """
    input_html = input_html.resolve()

    if not input_html.exists():
        raise FileNotFoundError(f"HTML file not found: {input_html}")

    html_content = input_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    text_lines = []

    for tag in iter_translatable_tags(soup):
        text_content = " ".join(" ".join(direct_text_nodes(tag)).split())
        if text_content:
            text_lines.append({
                "id": normalize_id(tag["id"]),
                "text": text_content,
            })

    return text_lines


def format_as_text_lines(text_lines: list[dict]) -> str:
    """
    Format extracted text as line-delimited text for processing.

    Args:
        text_lines: List of dicts from extract_tag_text()

    Returns:
        Formatted string: "id000000 {text}\nid000001 {text}\n..."
    """
    lines = []
    for item in text_lines:
        lines.append(f"{item['id']} {item['text']}")

    return "\n".join(lines)
