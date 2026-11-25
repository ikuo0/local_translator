"""Run free-text translation from the command line."""

import argparse
import sys

from requests import RequestException

from . import DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL, DIRECTIONS, translate_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate text between English and Japanese")
    parser.add_argument("--direction", choices=DIRECTIONS, required=True)
    parser.add_argument("--text", help="Text to translate. Otherwise read from standard input.")
    parser.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL)
    args = parser.parse_args()

    text = args.text
    if text is None:
        text = sys.stdin.read()

    try:
        translation = translate_text(
            text, args.direction, ollama_host=args.ollama_host, model=args.ollama_model,
        )
    except (ValueError, RuntimeError, RequestException) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    sys.stdout.write(translation)
    if not translation.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
