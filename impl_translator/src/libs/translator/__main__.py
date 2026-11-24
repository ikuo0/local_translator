import argparse
import sys
from pathlib import Path

from . import translate_page


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate a single-page PDF")
    parser.add_argument("--input-pdf", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ollama-host", default="http://ollama:11434")
    parser.add_argument("--ollama-model", default="qwen3:8b")
    args = parser.parse_args()
    try:
        print(
            translate_page(
                args.input_pdf.resolve(),
                args.output_dir.resolve(),
                args.ollama_host,
                args.ollama_model,
            )
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
