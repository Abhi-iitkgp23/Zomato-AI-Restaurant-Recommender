"""Safety helpers for untrusted LLM / user text."""

from __future__ import annotations

import html
import re

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(value: str | None, *, max_len: int = 2000, escape: bool = False) -> str:
    """Strip control chars, optionally HTML-escape, and truncate."""
    if not value:
        return ""
    text = _CONTROL_RE.sub("", str(value))
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "…"
    if escape:
        text = html.escape(text, quote=True)
    return text
