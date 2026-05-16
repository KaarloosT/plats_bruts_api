import re
import unicodedata


def slugify(text: str) -> str:
    """Normalize a string to an ASCII, lowercase, hyphen-separated slug."""
    # Normalize to NFKD to decompose accented characters
    normalized = unicodedata.normalize("NFKD", text)
    # Remove diacritical marks (combining characters)
    without_diacritics = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    # Convert to ASCII, removing any remaining non-ASCII characters
    ascii_only = without_diacritics.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    lowered = ascii_only.lower()
    # Replace sequences of whitespace and hyphens with a single hyphen
    # Then remove all other punctuation
    cleaned = re.sub(r"[\s-]+", "-", lowered)  # Collapse whitespace/hyphens to single hyphen
    cleaned = re.sub(r"[^\w-]", "", cleaned)   # Remove all punctuation except hyphens (keeps alphanumeric and underscores)
    cleaned = re.sub(r"_", "", cleaned)        # Remove underscores
    cleaned = re.sub(r"-+", "-", cleaned)      # Collapse multiple hyphens to single
    # Strip leading/trailing hyphens
    return cleaned.strip("-")
