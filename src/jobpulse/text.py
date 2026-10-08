from __future__ import annotations

import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser

_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "tr"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html or "")
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def to_day(value: str | int | float | None) -> str:
    """Normalize unix timestamps and ISO strings to YYYY-MM-DD (UTC)."""
    if value is None or value == "":
        return date.today().isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).date().isoformat()
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
