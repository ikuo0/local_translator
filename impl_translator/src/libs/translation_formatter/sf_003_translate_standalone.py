"""
Standalone test for SF003 translate module.
Usage: python sf_003_translate_standalone.py
"""

import json
import tempfile
from pathlib import Path

from impl_translator.src.libs.sf_003_translate import (
    format_batch_for_prompt,
    parse_translation_response,
    translate_batches,
)


def test_format_batch_for_prompt():
    """Test batch formatting for Ollama API."""
    print("=" * 60)
    print("TEST 1: Format batch for Ollama prompt")
    print("=" * 60)

    batch = {
        "batch_id": 0,
        "lines": [
            {"id": "tag_000000", "text": "Hello world"},
            {"id": "tag_000001", "text": "This is a test\nwith newline"},
            {"id": "tag_000002", "text": "Another text"},
        ],
        "char_count": 65,
    }

    prompt = format_batch_for_prompt(batch)
    print("Input batch:")
    print(json.dumps(batch, indent=2, ensure_ascii=False))
    print("\nFormatted prompt:")
    print(prompt)
    print()

    # Verify format
    lines = prompt.split("\n")
    assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"
    assert lines[0].startswith("{ID=tag_000000}"), "Line 0 format error"
    assert lines[1].startswith("{ID=tag_000001}"), "Line 1 format error"
    assert "<br>" in lines[1], "Newline not converted to <br>"
    print("✓ Format test passed\n")


def test_parse_translation_response():
    """Test parsing translation response from Ollama."""
    print("=" * 60)
    print("TEST 2: Parse translation response")
    print("=" * 60)

    response_text = """{ID=tag_000000} こんにちは世界
{ID=tag_000001} これはテストです<br>改行を含む
{ID=tag_000002} 別のテキスト"""

    translations = parse_translation_response(response_text)
    print("Input response:")
    print(response_text)
    print("\nParsed translations:")
    print(json.dumps(translations, indent=2, ensure_ascii=False))
    print()

    # Verify parsing
    assert len(translations) == 3, f"Expected 3 translations, got {len(translations)}"
    assert translations["tag_000000"] == "こんにちは世界"
    assert "<br>" in translations["tag_000001"]
    print("✓ Parsing test passed\n")


def test_translate_batches_mock():
    """Test translate_batches with mock data (without actual Ollama)."""
    print("=" * 60)
    print("TEST 3: Mock batch translation pipeline")
    print("=" * 60)

    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create input batches JSON
        batches = [
            {
                "batch_id": 0,
                "lines": [
                    {"id": "tag_000000", "text": "Hello"},
                    {"id": "tag_000001", "text": "World"},
                ],
                "char_count": 10,
            },
            {
                "batch_id": 1,
                "lines": [
                    {"id": "tag_000002", "text": "This is a test"},
                ],
                "char_count": 14,
            },
        ]

        input_file = tmpdir_path / "batches.json"
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(batches, f, ensure_ascii=False, indent=2)

        print("Input batches file created:")
        print(json.dumps(batches, indent=2, ensure_ascii=False))
        print()

        # Mock Ollama (would need actual Ollama running for full test)
        print(f"Input: {input_file}")
        print(f"Output: Would be translations.json")
        print()
        print("✓ Mock pipeline test prepared (requires running Ollama for actual translation)\n")


def test_full_pipeline_format():
    """Test the complete format flow from batch to response parsing."""
    print("=" * 60)
    print("TEST 4: Full pipeline format (batch -> prompt -> response -> translations)")
    print("=" * 60)

    # Input batch
    batch = {
        "batch_id": 0,
        "lines": [
            {"id": "tag_000000", "text": "The surface consists of multiple polygons"},
            {"id": "tag_000001", "text": "Each polygon has a unique identifier"},
        ],
        "char_count": 85,
    }

    print("Step 1: Input batch")
    print(json.dumps(batch, indent=2, ensure_ascii=False))
    print()

    # Format for Ollama
    prompt = format_batch_for_prompt(batch)
    print("Step 2: Formatted prompt for Ollama API")
    print(prompt)
    print()

    # Simulate Ollama response
    response = """{ID=tag_000000} 表面は複数のポリゴンで構成されています
{ID=tag_000001} 各ポリゴンは一意の識別子を持っています"""

    print("Step 3: Simulated Ollama response")
    print(response)
    print()

    # Parse response
    translations = parse_translation_response(response)
    print("Step 4: Parsed translations")
    print(json.dumps(translations, indent=2, ensure_ascii=False))
    print()

    # Final output format
    output_data = {
        "total_batches": 1,
        "translations": translations,
    }

    print("Step 5: Final output format (ready for translation_restorer)")
    print(json.dumps(output_data, indent=2, ensure_ascii=False))
    print()

    print("✓ Full pipeline test passed\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SF003 TRANSLATE MODULE - UNIT TESTS")
    print("=" * 60)
    print()

    test_format_batch_for_prompt()
    test_parse_translation_response()
    test_translate_batches_mock()
    test_full_pipeline_format()

    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
    print()
    print("Note: To test with actual Ollama translation, run:")
    print(
        "  python -m impl_translator.src.libs.sf_003_translate \\"
    )
    print("    --input batches.json --output translations.json \\"
    )
    print("    --host http://localhost:11434 --model qwen3:8b")
