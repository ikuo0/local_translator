import argparse
import sys
from pathlib import Path

from . import restore_translations_to_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore translated text back into HTML")
    parser.add_argument("--input-html", required=True, type=Path, help="Path to preprocessed HTML file")
    parser.add_argument("--translations", required=True, type=Path, help="Path to translations JSON file")
    parser.add_argument("--output", required=True, type=Path, help="Path to output HTML file")
    args = parser.parse_args()

    try:
        result = restore_translations_to_html(
            input_html=args.input_html.resolve(),
            translations_json=args.translations.resolve(),
            output_html=args.output.resolve(),
        )
        print(result)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
