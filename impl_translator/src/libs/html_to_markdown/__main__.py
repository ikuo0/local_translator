"""Run HTML-to-Markdown conversion from the command line."""

import argparse
import sys
from pathlib import Path

from . import convert_html_to_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert one HTML file to Markdown")
    parser.add_argument("--input", required=True, type=Path, help="Path to input HTML")
    parser.add_argument("--output", required=True, type=Path, help="Path to output Markdown")
    args = parser.parse_args()

    try:
        print(convert_html_to_markdown(args.input, args.output))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
