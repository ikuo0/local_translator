"""PDF to HTML conversion using Docling."""

import json
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter


def convert_pdf_to_html(
    input_pdf: Path,
    output_dir: Path,
    split_pages: bool = False,
    combine: bool = False,
) -> Path:
    """
    Convert a PDF file to HTML using Docling.

    Args:
        input_pdf: Path to input PDF file
        output_dir: Directory to save the converted HTML file(s)
        split_pages: If True, save each page as a separate HTML file
        combine: If True, combine all pages into a single HTML file (default behavior)

    Returns:
        Path to the generated HTML file or directory (if split_pages=True)

    Raises:
        FileNotFoundError: If input PDF does not exist
        RuntimeError: If conversion fails
    """
    input_pdf = input_pdf.resolve()
    output_dir = Path(output_dir).resolve()

    if not input_pdf.exists():
        raise FileNotFoundError(f"PDF file not found: {input_pdf}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert PDF to Docling document
    converter = DocumentConverter()
    result = converter.convert(input_pdf)

    if result.document is None:
        raise RuntimeError(f"Failed to convert PDF: {input_pdf}")

    doc = result.document
    num_pages = doc.num_pages()

    if split_pages:
        return _export_pages_split(doc, input_pdf, output_dir, num_pages)
    else:
        return _export_combined(doc, input_pdf, output_dir)


def _export_combined(doc, input_pdf: Path, output_dir: Path) -> Path:
    """Export all pages into a single HTML file."""
    output_html = output_dir / f"{input_pdf.stem}.html"
    html_content = doc.export_to_html()
    output_html.write_text(html_content, encoding="utf-8")
    return output_html


def _export_pages_split(doc, input_pdf: Path, output_dir: Path, num_pages: int) -> Path:
    """Export each page as a separate HTML file and create index.json."""
    pages_dir = output_dir / f"{input_pdf.stem}_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Metadata for index.json
    index_data = {
        "source_pdf": str(input_pdf),
        "total_pages": num_pages,
        "pages": []
    }

    # Export each page
    for page_num in range(1, num_pages + 1):
        html_content = doc.export_to_html(page_no=page_num)
        page_file = pages_dir / f"page_{page_num:04d}.html"
        page_file.write_text(html_content, encoding="utf-8")

        index_data["pages"].append({
            "page_number": page_num,
            "file": f"page_{page_num:04d}.html",
            "size_bytes": len(html_content.encode("utf-8"))
        })

    # Write index.json
    index_file = output_dir / "index.json"
    index_file.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return pages_dir


