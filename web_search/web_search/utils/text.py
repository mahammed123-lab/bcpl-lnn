"""
JARVIS Web Search — Text cleaning utilities.

Strips HTML, markdown artefacts, and excessive whitespace from raw
snippets returned by search providers.
"""
import re

try:
    from bs4 import BeautifulSoup
    _BS4_OK = True
except ImportError:
    _BS4_OK = False


def clean_text(text: str, max_chars: int = 2000) -> str:
    """Strip HTML, markdown links, and URLs from *text*."""
    if not text:
        return ""
    if _BS4_OK:
        text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(http.*?\)", "", text)
    text = re.sub(r"https?://\S+", "", text)
    return text.strip()[:max_chars]


def extract_clean_text(raw: str, max_chars: int = 3000) -> str:
    """Heavier extraction: strip tags, markdown, short lines."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[*\-]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"https?://\S+", "", text)
    lines = [
        ln.strip()
        for ln in text.splitlines()
        if len(ln.strip()) >= 20 and re.search(r"[a-z]{3,}", ln)
    ]
    return re.sub(r"\s{2,}", " ", " ".join(lines)).strip()[:max_chars]
