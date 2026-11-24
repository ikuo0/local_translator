"""
SR1000 integrated command: PDF to Japanese HTML/PDF translation
Combines all libs modules (docling_converter, html_preproc, html_text_extractor,
batch_splitter, translation_formatter, translation_restorer)
"""

import argparse
import logging
import sys
from pathlib import Path

from impl_translator.src.features.SR1000.sr1000_pipeline import SR1000Pipeline


def setup_logging(log_file: Path) -> logging.Logger:
    """Configure logging."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("SR1000")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)
    
    # Console handler (for real-time display)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )
    logger.addHandler(console_handler)

    return logger


def translate_pdf(
    input_pdf: Path,
    working_dir: Path,
    log_file: Path,
    ollama_host: str = "http://localhost:11434",
    ollama_model: str = "qwen3:8b",
    temperature: float = 0.3,
    resume: bool = False,
) -> int:
    """
    Translate a PDF document page by page.

    Returns:
        0 if successful, 1 if any page failed
    """
    logger = setup_logging(log_file)
    logger.info("SR1000 Pipeline started")
    logger.info(f"Input PDF: {input_pdf}")
    logger.info(f"Working directory: {working_dir}")

    if not input_pdf.exists():
        logger.error(f"Input PDF not found: {input_pdf}")
        return 1

    # Import pymupdf to get page count
    try:
        import pymupdf

        with pymupdf.open(input_pdf) as pdf:
            page_count = len(pdf)
    except Exception as e:
        logger.error(f"Failed to read PDF: {e}")
        return 1

    logger.info(f"PDF has {page_count} pages")

    # Initialize pipeline
    pipeline = SR1000Pipeline(working_dir=working_dir, logger=logger)

    # Process each page
    failed_pages = []
    completed_pages = []

    for page_number in range(1, page_count + 1):
        page_id = f"page_{page_number:06d}"
        logger.info(f"Processing {page_id} ({page_number}/{page_count})")

        try:
            success = pipeline.process_page(
                page_id=page_id,
                input_pdf=input_pdf,
                page_number=page_number,
                ollama_host=ollama_host,
                ollama_model=ollama_model,
                temperature=temperature,
                resume=resume,
            )

            if success:
                completed_pages.append(page_number)
                logger.info(f"✓ {page_id} completed")
            else:
                failed_pages.append(page_number)
                logger.warning(f"✗ {page_id} failed")

        except Exception as e:
            logger.error(f"Exception processing {page_id}: {e}")
            failed_pages.append(page_number)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Processing complete: {len(completed_pages)} completed, {len(failed_pages)} failed")

    if failed_pages:
        logger.warning(f"Failed pages: {failed_pages}")
        return 1
    else:
        logger.info("All pages processed successfully!")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="SR1000: Translate PDF to Japanese using Ollama"
    )

    parser.add_argument(
        "--input-pdf",
        type=Path,
        required=True,
        help="Input PDF file",
    )
    parser.add_argument(
        "--working-dir",
        type=Path,
        required=True,
        help="Working directory for intermediate files and state",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        required=True,
        help="Log file path",
    )
    parser.add_argument(
        "--ollama-host",
        type=str,
        default="http://localhost:11434",
        help="Ollama host URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="qwen3:8b",
        help="Ollama model name (default: qwen3:8b)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Translation temperature (default: 0.3)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous progress",
    )

    args = parser.parse_args()

    exit_code = translate_pdf(
        input_pdf=args.input_pdf,
        working_dir=args.working_dir,
        log_file=args.log_file,
        ollama_host=args.ollama_host,
        ollama_model=args.ollama_model,
        temperature=args.temperature,
        resume=args.resume,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
