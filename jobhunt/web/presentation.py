"""Pure display helpers registered as Jinja globals (labels and CSS classes)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from io import StringIO

from jobhunt.reports.console import format_remote_label


def score_class(score: int | None) -> str:
    if score is None:
        return "score-none"
    if score >= 80:
        return "score-high"
    if score >= 60:
        return "score-mid"
    if score >= 40:
        return "score-low"
    return "score-min"


def remote_label(value: str | None) -> str:
    return format_remote_label(value or "unknown_remote_status")


def remote_class(value: str | None) -> str:
    return "remote-" + (value or "unknown_remote_status")


def status_label(value: str | None) -> str:
    return (value or "found").replace("_", " ").title()


def status_class(value: str | None) -> str:
    return "status-" + (value or "found")


def humanize(value: str | None) -> str:
    return (value or "").replace("_", " ").title()


def reason_label(reason: str) -> str:
    """Humanize a scorer reason/concern, e.g. 'strong: backend' -> 'Backend (strong)'."""
    for prefix, suffix in (("strong: ", "strong"), ("learning: ", "to learn")):
        if reason.startswith(prefix):
            return f"{reason[len(prefix):].strip().title()} ({suffix})"
    if reason.startswith("excluded keyword: "):
        return f"Excluded: {reason[len('excluded keyword: '):].strip()}"
    return reason[:1].upper() + reason[1:] if reason else reason


_BLOCK_TAGS = {"p", "br", "li", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._out = StringIO()

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self._out.write("\n• ")
        elif tag in _BLOCK_TAGS:
            self._out.write("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self._out.write("\n")

    def handle_data(self, data):
        self._out.write(data)

    def text(self) -> str:
        return self._out.getvalue()


def strip_html(value: str | None) -> str:
    """Render source HTML descriptions as readable plain text (tags removed, blocks kept)."""
    if not value:
        return ""
    parser = _TextExtractor()
    parser.feed(value)
    text = parser.text()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


TEMPLATE_GLOBALS = {
    "score_class": score_class,
    "remote_label": remote_label,
    "remote_class": remote_class,
    "status_label": status_label,
    "status_class": status_class,
    "humanize": humanize,
    "reason_label": reason_label,
    "strip_html": strip_html,
}
