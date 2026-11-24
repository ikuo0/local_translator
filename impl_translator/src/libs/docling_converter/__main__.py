import argparse
import sys
from pathlib import Path

from . import convert_pdf_to_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert PDF to HTML using Docling")
    parser.add_argument("--input-pdf", required=True, type=Path, help="Path to input PDF file")
    parser.add_argument("--working", required=True, type=str, help="Working directory (format: dir=/path)")
    
    # Mutually exclusive options
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--split-pages",
        action="store_true",
        help="Export each page as separate HTML file with index.json"
    )
    mode_group.add_argument(
        "--combine",
        action="store_true",
        help="Combine all pages into single HTML file"
    )
    
    args = parser.parse_args()

    # Parse working directory
    if not args.working.startswith("dir="):
        print("Error: --working format must be 'dir=/path'", file=sys.stderr)
        return 1
    
    output_dir = Path(args.working[4:]).resolve()

    try:
        result = convert_pdf_to_html(
            input_pdf=args.input_pdf.resolve(),
            output_dir=output_dir,
            split_pages=args.split_pages,
            combine=args.combine,
        )
        print(result)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

