"""Export the PDF and page-by-page text and Markdown for an SR1000 job."""

from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import Comment, Declaration, Doctype, ProcessingInstruction

from impl_translator.src.libs.html_to_markdown import convert_html_to_markdown


_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "td",
    "th", "tr", "ul",
}
_IGNORED_TAGS = {"head", "script", "style", "template"}
_FIGURE_TAGS = {"canvas", "figure", "img", "picture", "svg"}


def extract_page_text(html: str) -> str:
    """Keep visible text in document order and replace layout boundaries with spaces."""
    document = BeautifulSoup(html, "html.parser")
    chunks = []
    figure_number = 0

    def visit(node: Tag | NavigableString) -> None:
        nonlocal figure_number
        if isinstance(node, (Comment, Declaration, Doctype, ProcessingInstruction)):
            return
        if isinstance(node, NavigableString):
            chunks.append(str(node))
            return
        if node.name in _IGNORED_TAGS or node.has_attr("hidden"):
            return
        if node.name in _FIGURE_TAGS:
            figure_number += 1
            chunks.append(f" [[figure{figure_number}]] ")
            if node.name == "figure":
                for caption in node.find_all("figcaption", recursive=False):
                    visit(caption)
            return

        is_table = node.name == "table"
        is_block = node.name in _BLOCK_TAGS
        if is_block:
            chunks.append(" [[table begin]] " if is_table else " ")
        for child in node.children:
            visit(child)
        if is_block:
            chunks.append(" [[table end]] " if is_table else " ")

    visit(document.body or document)
    return " ".join("".join(chunks).split())


def export_translated_pages(
    html_pages: Iterable[tuple[Path, Path]], phase_dir: Path, pdf_name: str,
) -> Path:
    """Export ordered pairs of original and translated HTML files."""
    pdf_dir = phase_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = pdf_dir / pdf_name
    page_exports = {"text": ".txt", "md_en": ".md", "md_jp": ".md"}

    with TemporaryDirectory(prefix=".export-", dir=phase_dir) as temporary_dir:
        staging = Path(temporary_dir)
        temporary_pdf = staging / pdf_name
        (staging / "text").mkdir()
        translated_pages = []
        page_ids = set()
        for original_html, translated_html in html_pages:
            page_id = translated_html.parent.name
            text = extract_page_text(translated_html.read_text(encoding="utf-8"))
            (staging / "text" / f"{page_id}.txt").write_text(
                f"{text}\n" if text else "", encoding="utf-8",
            )
            convert_html_to_markdown(original_html, staging / "md_en" / f"{page_id}.md")
            convert_html_to_markdown(translated_html, staging / "md_jp" / f"{page_id}.md")
            translated_pages.append(translated_html)
            page_ids.add(page_id)

        build_translated_pdf(translated_pages, temporary_pdf)
        for directory, suffix in page_exports.items():
            destination = phase_dir / directory
            destination.mkdir(exist_ok=True)
            for page_id in sorted(page_ids):
                filename = f"{page_id}{suffix}"
                (staging / directory / filename).replace(destination / filename)
            for old_page in destination.glob(f"page_*{suffix}"):
                page_number = old_page.stem.removeprefix("page_")
                if page_number.isdecimal() and old_page.stem not in page_ids:
                    old_page.unlink()
        temporary_pdf.replace(output_pdf)

    return output_pdf


def build_translated_pdf(html_pages: Iterable[Path], output_pdf: Path) -> None:
    """Render each HTML file on one A4 sheet, scaling oversized content."""
    paper = pymupdf.paper_rect("a4")
    content = paper + (36, 36, -36, -36)

    with TemporaryDirectory(prefix=".sf005-", dir=output_pdf.parent) as temporary_dir:
        temporary_pdf = Path(temporary_dir) / output_pdf.name
        writer = pymupdf.DocumentWriter(str(temporary_pdf))
        try:
            for html_path in html_pages:
                story = pymupdf.Story(
                    html=html_path.read_text(encoding="utf-8"),
                    archive=pymupdf.Archive(str(html_path.parent)),
                )
                fit = story.fit_height(
                    content.width, height_min=content.height, height_max=14400, delta=1,
                )
                if not fit.big_enough:
                    raise ValueError(f"Unable to fit HTML content on a PDF page: {html_path}")
                scale = content.height / fit.rect.height
                placement = pymupdf.Matrix(scale, 0, 0, scale, content.x0, content.y0)
                device = writer.begin_page(paper)
                story.draw(device, placement)
                writer.end_page()
        finally:
            writer.close()
        temporary_pdf.replace(output_pdf)
