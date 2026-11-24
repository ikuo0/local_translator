"""
CLI interface for translation_formatter module.
"""

import argparse
import json
from pathlib import Path

from impl_translator.src.libs.translation_formatter import (
    translate_batch,
    translate_batches,
    translate_batches_with_metadata,
)



def main():
    parser = argparse.ArgumentParser(
        description="translation_formatter: Format and translate batches using Ollama"
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input batches JSON file (from batch_splitter)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output translations JSON file",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:11434",
        help="Ollama host URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3:8b",
        help="Model name (default: qwen3:8b)",
    )
    parser.add_argument(
        "--keep-alive",
        type=str,
        default="5m",
        help="Keep-alive time for model (default: 5m)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Temperature for translation (default: 0.3)",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Include metadata in output JSON",
    )
    parser.add_argument(
        "--single-batch",
        type=int,
        help="Translate only a single batch by ID",
    )

    args = parser.parse_args()

    # Input file check
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        exit(1)

    # Single batch mode
    if args.single_batch is not None:
        with open(args.input, "r", encoding="utf-8") as f:
            batches = json.load(f)

        # Find batch by ID
        batch = None
        for b in batches:
            if b["batch_id"] == args.single_batch:
                batch = b
                break

        if batch is None:
            print(f"Error: Batch {args.single_batch} not found")
            exit(1)

        print(f"Translating batch {args.single_batch}...")
        result = translate_batch(
            batch,
            ollama_host=args.host,
            model=args.model,
            keep_alive=args.keep_alive,
            temperature=args.temperature,
        )

        output_data = {
            "batch_id": args.single_batch,
            "translations": result,
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Translations saved to {args.output}")
        return

    # Multiple batches mode
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Host: {args.host}")
    print(f"Model: {args.model}")
    print()

    if args.metadata:
        result = translate_batches_with_metadata(
            args.input,
            args.output,
            ollama_host=args.host,
            model=args.model,
            keep_alive=args.keep_alive,
            temperature=args.temperature,
        )
        print()
        print(f"✓ Translations saved to {args.output}")
        print(f"  Total batches: {result['metadata']['total_batches']}")
        print(f"  Total translations: {len(result['translations'])}")
    else:
        result = translate_batches(
            args.input,
            args.output,
            ollama_host=args.host,
            model=args.model,
            keep_alive=args.keep_alive,
            temperature=args.temperature,
        )
        print()
        print(f"✓ Translations saved to {args.output}")
        print(f"  Total batches: {result['total_batches']}")
        print(f"  Total translations: {len(result['translations'])}")


if __name__ == "__main__":
    main()
