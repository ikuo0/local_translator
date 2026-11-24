"""Split text lines into batches for translation."""

from pathlib import Path


def split_text_into_batches(input_text: Path, max_chars: int = 1500) -> list[dict]:
    """
    Split text lines into batches for translation.

    Each batch:
    - Contains consecutive lines from the input
    - Total character count ≤ max_chars
    - Single line exceeding max_chars is kept as a single batch

    Args:
        input_text: Path to text file with lines in format: {ID=tag_XXXXXX} {text}
        max_chars: Maximum characters per batch (default: 1500)

    Returns:
        List of batch dicts:
        [
            {
                "batch_id": 0,
                "lines": [
                    {"id": "tag_000000", "text": "..."},
                    {"id": "tag_000001", "text": "..."}
                ],
                "char_count": 1234
            },
            ...
        ]

    Raises:
        FileNotFoundError: If input file does not exist
        ValueError: If format is invalid
    """
    input_text = input_text.resolve()

    if not input_text.exists():
        raise FileNotFoundError(f"Text file not found: {input_text}")

    content = input_text.read_text(encoding="utf-8")
    text_lines = content.strip().split("\n")

    # Parse lines
    parsed_lines = []
    for line in text_lines:
        if not line.strip():
            continue

        # Format: {ID=tag_XXXXXX} {text}
        if not line.startswith("{ID="):
            raise ValueError(f"Invalid line format: {line}")

        # Extract ID and text
        end_id_pos = line.find("}")
        if end_id_pos == -1:
            raise ValueError(f"Invalid line format: {line}")

        tag_id = line[4:end_id_pos]  # Extract from {ID= to }
        text = line[end_id_pos + 2:] if end_id_pos + 2 < len(line) else ""  # Skip "} "

        parsed_lines.append({
            "id": tag_id,
            "text": text,
            "line": line,
        })

    # Split into batches
    batches = []
    current_batch_lines = []
    current_char_count = 0
    batch_id = 0

    for line_data in parsed_lines:
        line_char_count = len(line_data["line"])

        # Check if adding this line would exceed limit
        if current_batch_lines and current_char_count + line_char_count + 1 > max_chars:
            # Start new batch
            batches.append({
                "batch_id": batch_id,
                "lines": current_batch_lines,
                "char_count": current_char_count,
            })
            batch_id += 1
            current_batch_lines = []
            current_char_count = 0

        # Add line to current batch
        current_batch_lines.append({
            "id": line_data["id"],
            "text": line_data["text"],
        })
        current_char_count += line_char_count + 1  # +1 for newline

    # Add final batch
    if current_batch_lines:
        batches.append({
            "batch_id": batch_id,
            "lines": current_batch_lines,
            "char_count": current_char_count,
        })

    return batches


def format_batch_for_translation(batch: dict) -> str:
    """
    Format a batch for sending to translation API.

    Args:
        batch: Batch dict from split_text_into_batches()

    Returns:
        Formatted string with all lines joined
    """
    lines = []
    for line_data in batch["lines"]:
        lines.append(f"{{ID={line_data['id']}}} {line_data['text']}")

    return "\n".join(lines)
