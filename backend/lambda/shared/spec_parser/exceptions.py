"""
Custom exceptions for spec parsing and validation.
Provides context for user-friendly error messages.
"""

from typing import Any, Optional


class SpecParserError(Exception):
    """Base exception for all spec parsing errors."""

    pass


class ParseError(SpecParserError):
    """YAML parsing failed."""

    def __init__(
        self, message: str, line: Optional[int] = None, column: Optional[int] = None
    ):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.line:
            return f"Parse error at line {self.line}: {self.message}"
        return f"Parse error: {self.message}"


class ValidationError(SpecParserError):
    """Schema validation failed."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
    ):
        self.message = message
        self.field = field
        self.expected = expected
        self.actual = actual
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = []

        if self.field:
            parts.append(f"Validation error in '{self.field}'")
        else:
            parts.append("Validation error")

        parts.append(self.message)

        if self.expected is not None and self.actual is not None:
            parts.append(f"Expected: {self.expected}, Got: {self.actual}")
        elif self.expected is not None:
            parts.append(f"Expected: {self.expected}")

        return " - ".join(parts)


class SecurityError(SpecParserError):
    """Potentially malicious YAML detected."""

    def __init__(self, message: str, pattern: Optional[str] = None):
        self.message = message
        self.pattern = pattern
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.pattern:
            return f"Security violation: {self.message} (detected: {self.pattern})"
        return f"Security violation: {self.message}"
