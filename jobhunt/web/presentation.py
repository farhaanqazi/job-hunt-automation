"""Pure display helpers registered as Jinja globals (labels and CSS classes)."""

from __future__ import annotations

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


TEMPLATE_GLOBALS = {
    "score_class": score_class,
    "remote_label": remote_label,
    "remote_class": remote_class,
    "status_label": status_label,
    "status_class": status_class,
    "humanize": humanize,
}
