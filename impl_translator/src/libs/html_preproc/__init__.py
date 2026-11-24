"""HTML preprocessing: remove styling tags and add sequential IDs."""

from pathlib import Path

from bs4 import BeautifulSoup


def preprocess_html(input_html: Path, output_html: Path) -> Path:
    """
    Preprocess HTML by removing styling tags and adding sequential IDs.

    Operations:
    1. Remove tags: b, strong, i, em, span, font, u, script
    2. Add sequential ID to all tags (for translation mapping)

    Args:
        input_html: Path to input HTML file
        output_html: Path to output HTML file

    Returns:
        Path to the generated HTML file

    Raises:
        FileNotFoundError: If input HTML does not exist
        RuntimeError: If processing fails
    """
    input_html = input_html.resolve()
    output_html = output_html.resolve()

    if not input_html.exists():
        raise FileNotFoundError(f"HTML file not found: {input_html}")

    output_html.parent.mkdir(parents=True, exist_ok=True)

    # Read HTML
    html_content = input_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    # Tags to remove (unwrap: keep content, remove tag)
    unwrap_tags = {"b", "strong", "i", "em", "span", "font", "u"}
    
    # Tags to remove entirely (content removed too)
    remove_tags = {"script"}

    # Remove script tags entirely
    for tag in soup.find_all(remove_tags):
        tag.decompose()

    # Unwrap styling tags (keep content, remove tag)
    for tag in soup.find_all(unwrap_tags):
        tag.unwrap()

    # Add sequential IDs to all tags
    tag_id_counter = 0
    for tag in soup.find_all(True):  # True means find all tags
        # Skip tags without a name (e.g., NavigableString)
        if tag.name:
            tag["id"] = f"id{tag_id_counter:06d}"
            tag_id_counter += 1

    # Write output
    output_html.write_text(str(soup), encoding="utf-8")
    return output_html
