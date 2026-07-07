"""Input validation and sanitization helpers."""
from __future__ import annotations

import html
import os
import re
from typing import Any, Optional

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
_SQL_PATTERNS = (
    re.compile(r"--|/\*|\*/|;\s*(select|insert|update|delete|drop|alter|truncate)\b", re.IGNORECASE),
    re.compile(r"\bunion\s+select\b", re.IGNORECASE),
    re.compile(r"\bor\b\s+['\"]?1['\"]?\s*=\s*['\"]?1\b", re.IGNORECASE),
)
_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


class InputValidator:
    """Validate and sanitize common API inputs."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Strip HTML, control characters, and enforce length limits."""
        if value is None:
            return ""
        sanitized = html.unescape(str(value))
        sanitized = _HTML_TAG_RE.sub("", sanitized)
        sanitized = _CONTROL_CHAR_RE.sub("", sanitized)
        return sanitized.strip()[:max_length]

    @staticmethod
    def validate_email(email: str) -> bool:
        """Return whether an email address matches a reasonable pattern."""
        if not email:
            return False
        return _EMAIL_RE.match(email) is not None

    @staticmethod
    def validate_sql_input(value: Optional[str]) -> bool:
        """Reject obviously suspicious SQL fragments as a defense-in-depth check."""
        if value is None:
            return False
        return not any(pattern.search(value) for pattern in _SQL_PATTERNS)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove path traversal and unsafe characters from filenames."""
        if not filename:
            return ""
        safe_name = os.path.basename(filename)
        safe_name = safe_name.replace("..", "")
        return _FILENAME_RE.sub("_", safe_name)

    @staticmethod
    def validate_json_depth(data: Any, max_depth: int = 10) -> bool:
        """Return whether nested JSON-like data stays within max depth."""
        def _depth(value: Any, current_depth: int) -> bool:
            if current_depth > max_depth:
                return False
            if isinstance(value, dict):
                return all(_depth(child, current_depth + 1) for child in value.values())
            if isinstance(value, list):
                return all(_depth(child, current_depth + 1) for child in value)
            return True

        return _depth(data, 0)
