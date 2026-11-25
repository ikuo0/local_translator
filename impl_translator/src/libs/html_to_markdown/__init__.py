"""Convert an HTML file to Markdown."""

from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


def convert_html_to_markdown(input_html: Path, output_markdown: Path) -> Path:
    """Convert one UTF-8 HTML file to one UTF-8 Markdown file and return its path."""
    input_html = input_html.resolve()
    output_markdown = output_markdown.resolve()
    if input_html == output_markdown:
        raise ValueError("Input HTML and output Markdown must be different files")

    document = BeautifulSoup(input_html.read_text(encoding="utf-8-sig"), "html.parser")
    content = document.body if document.body is not None else document
    for tag in content.find_all(["head", "script", "style", "template"]):
        tag.decompose()

    markdown = MarkdownConverter(heading_style="ATX").convert_soup(content).strip("\n")
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(f"{markdown}\n" if markdown else "", encoding="utf-8")
    return output_markdown
