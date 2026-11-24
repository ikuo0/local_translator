import argparse
import json
import sys
from pathlib import Path

from . import split_text_into_batches


def main() -> int:
    parser = argparse.ArgumentParser(description="Split text into batches for translation")
    parser.add_argument("--input", required=True, type=Path, help="Path to text file")
    parser.add_argument("--output", required=True, type=Path, help="Path to output JSON file")
    parser.add_argument("--max-chars", type=int, default=1500, help="Max chars per batch (default: 1500)")
    args = parser.parse_args()

    try:
        batches = split_text_into_batches(args.input.resolve(), max_chars=args.max_chars)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(batches, indent=2, ensure_ascii=False), encoding="utf-8")

        print(args.output)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
