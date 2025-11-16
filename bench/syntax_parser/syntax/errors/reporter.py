"""
Error reporting and collection for the 1C syntax parser.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Error:
    """
    Represents a syntax, type, or semantic error.

    Attributes:
        message: Human-readable error message
        line: Line number where error occurred (1-indexed)
        column: Column number where error occurred (1-indexed)
        error_type: Type of error ('syntax', 'type', 'semantic')
    """
    message: str
    line: int
    column: int
    error_type: str = 'syntax'

    def __str__(self) -> str:
        """Format error as a string."""
        return f"[{self.error_type.upper()}] Line {self.line}:{self.column}: {self.message}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Error({self.message!r}, {self.line}, {self.column}, {self.error_type!r})"


class ErrorReporter:
    """
    Collects and formats errors found during parsing and type checking.
    """

    def __init__(self):
        """Initialize an empty error reporter."""
        self.errors: List[Error] = []

    def add_error(
        self,
        message: str,
        line: int = 0,
        column: int = 0,
        error_type: str = 'syntax'
    ) -> None:
        """
        Add an error to the collection.

        Args:
            message: Error message
            line: Line number (1-indexed)
            column: Column number (1-indexed)
            error_type: Type of error ('syntax', 'type', 'semantic')
        """
        self.errors.append(Error(message, line, column, error_type))

    def add_syntax_error(self, message: str, line: int = 0, column: int = 0) -> None:
        """Add a syntax error."""
        self.add_error(message, line, column, 'syntax')

    def add_type_error(self, message: str, line: int = 0, column: int = 0) -> None:
        """Add a type error."""
        self.add_error(message, line, column, 'type')

    def add_semantic_error(self, message: str, line: int = 0, column: int = 0) -> None:
        """Add a semantic error."""
        self.add_error(message, line, column, 'semantic')

    def has_errors(self) -> bool:
        """Check if any errors have been reported."""
        return len(self.errors) > 0

    def error_count(self) -> int:
        """Get the total number of errors."""
        return len(self.errors)

    def get_errors(self) -> List[Error]:
        """Get the list of all errors."""
        return self.errors

    def clear(self) -> None:
        """Clear all errors."""
        self.errors.clear()

    def format_errors(self, max_errors: int = None) -> str:
        """
        Format all errors as a multi-line string.

        Args:
            max_errors: Maximum number of errors to display (None for all)

        Returns:
            Formatted error messages
        """
        if not self.errors:
            return "No errors found."

        # Sort errors by location (line, then column)
        sorted_errors = sorted(self.errors, key=lambda e: (e.line, e.column))

        # Limit errors if requested
        if max_errors is not None:
            displayed_errors = sorted_errors[:max_errors]
            remaining = len(sorted_errors) - max_errors
        else:
            displayed_errors = sorted_errors
            remaining = 0

        # Format each error
        lines = [str(error) for error in displayed_errors]

        # Add summary
        if remaining > 0:
            lines.append(f"... and {remaining} more error(s)")

        return '\n'.join(lines)

    def format_summary(self) -> str:
        """
        Format a summary of errors by type.

        Returns:
            Summary string
        """
        if not self.errors:
            return "No errors found."

        # Count errors by type
        type_counts = {}
        for error in self.errors:
            type_counts[error.error_type] = type_counts.get(error.error_type, 0) + 1

        # Format summary
        parts = []
        for error_type, count in sorted(type_counts.items()):
            parts.append(f"{count} {error_type} error(s)")

        return f"Found {len(self.errors)} total error(s): " + ", ".join(parts)

    def __str__(self) -> str:
        """String representation shows formatted errors."""
        return self.format_errors()

    def __repr__(self) -> str:
        """Debug representation."""
        return f"ErrorReporter(errors={len(self.errors)})"
