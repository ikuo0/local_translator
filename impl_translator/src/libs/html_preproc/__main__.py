import argparse
import sys
from pathlib import Path

from . import preprocess_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess HTML: remove styling tags and add sequential IDs")
    parser.add_argument("--input", required=True, type=Path, help="Path to input HTML file")
    parser.add_argument("--output", required=True, type=Path, help="Path to output HTML file")
    args = parser.parse_args()

    try:
        result = preprocess_html(
            input_html=args.input.resolve(),
            output_html=args.output.resolve(),
        )
        print(result)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
