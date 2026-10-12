import re


def slugify(text, separator="-"):
    """Turn text into a URL slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", separator, text)
    return text.strip(separator)
