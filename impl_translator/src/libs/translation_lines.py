"""Read translation lines and recognize IDs from older jobs."""

import re

LEGACY_ID = re.compile(r"tag_([0-9]{6,})")
TRANSLATION_LINE = re.compile(r"(id[0-9]{6,}|tag_[0-9]{6,})(?:[ \t]+(.*))?")


def normalize_id(element_id: str) -> str:
    legacy = LEGACY_ID.fullmatch(element_id)
    return f"id{legacy[1]}" if legacy else element_id


def parse_translation_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if line.startswith("{ID="):
        element_id, separator, text = line[4:].partition("}")
        if separator:
            return element_id, text.strip()
        return None

    match = TRANSLATION_LINE.fullmatch(line)
    if match:
        return match[1], match[2] or ""
    return None
