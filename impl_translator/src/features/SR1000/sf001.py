"""SF001: Convert one source PDF page to HTML."""

from pathlib import Path
from threading import Lock

import pymupdf

from impl_translator.src.libs.docling_converter import convert_pdf_to_html


_PDF_LOCK = Lock()


def count_pages(input_pdf: Path) -> int:
    """Read the number of pages in the source PDF."""
    with _PDF_LOCK, pymupdf.open(input_pdf) as pdf:
        return len(pdf)


def convert_page_to_html(input_pdf: Path, page_number: int, output_dir: Path) -> Path:
    """Convert a one-based PDF page number and return the generated HTML path."""
    temp_pdf = output_dir / "temp_page.pdf"
    with _PDF_LOCK, pymupdf.open(input_pdf) as pdf:
        if not 1 <= page_number <= len(pdf):
            raise ValueError(f"Page {page_number} out of range")
        with pymupdf.open() as single_page:
            single_page.insert_pdf(pdf, from_page=page_number - 1, to_page=page_number - 1)
            single_page.save(temp_pdf)

    converted_html = convert_pdf_to_html(temp_pdf, output_dir / "work")
    output_html = output_dir / "page.html"
    output_html.write_text(converted_html.read_text(encoding="utf-8"), encoding="utf-8")
    temp_pdf.unlink()
    converted_html.unlink()
    return output_html
