"""Run SR1200 from the command line."""

import argparse
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from requests import RequestException

from . import DEFAULT_CONTEXT_TOKENS, DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL, ask


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask a question using Ollama")
    parser.add_argument("--text", help="Question. Otherwise read from standard input.")
    parser.add_argument("--history-file", type=Path, help="Persist conversation history in this JSON file.")
    parser.add_argument("--context-tokens", type=int, default=DEFAULT_CONTEXT_TOKENS)
    parser.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL)
    args = parser.parse_args()

    text = args.text
    if text is None:
        text = sys.stdin.read()
    history_file = args.history_file

    try:
        history = None
        if history_file is not None and history_file.exists():
            history = json.loads(history_file.read_text(encoding="utf-8"))
        result = ask(
            text, keep_history=history_file is not None, history=history,
            context_tokens=args.context_tokens, ollama_host=args.ollama_host,
            model=args.ollama_model,
        )
        if history_file is not None:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=history_file.parent, delete=False,
            ) as file:
                temporary_path = Path(file.name)
                try:
                    json.dump(result["history"], file, ensure_ascii=False, indent=2)
                    file.close()
                    temporary_path.replace(history_file)
                finally:
                    temporary_path.unlink(missing_ok=True)
    except (OSError, ValueError, RuntimeError, RequestException) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(result["answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
