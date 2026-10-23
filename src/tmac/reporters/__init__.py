"""Reporters module for TMAC."""

from collections.abc import Callable

from tmac.reporters.base import BaseReporter
from tmac.reporters.html import HTMLReporter
from tmac.reporters.json_report import JSONReporter
from tmac.reporters.markdown import MarkdownReporter

REPORTERS: dict[str, Callable[[], BaseReporter]] = {
    "html": HTMLReporter,
    "json": JSONReporter,
    "md": MarkdownReporter,
}


def get_reporter(fmt: str) -> BaseReporter:
    """Return a reporter for 'html', 'json' or 'md' (unknown formats fall back to JSON/SARIF)."""
    return REPORTERS.get(fmt, JSONReporter)()
