import argparse
import sys
from pathlib import Path

from . import extract_tag_text, format_as_text_lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from HTML on a per-tag basis")
    parser.add_argument("--input", required=True, type=Path, help="Path to preprocessed HTML file")
    parser.add_argument("--output", required=True, type=Path, help="Path to output text file")
    args = parser.parse_args()

    try:
        text_lines = extract_tag_text(args.input.resolve())
        formatted_text = format_as_text_lines(text_lines)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted_text, encoding="utf-8")

        print(args.output)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
