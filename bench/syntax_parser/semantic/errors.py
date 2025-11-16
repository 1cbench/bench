"""
Semantic error definitions for 1C language analyzer.
"""

from dataclasses import dataclass


@dataclass
class SemanticError:
    """
    Represents a semantic error found during analysis.

    Attributes:
        message: Human-readable error message
        line: Line number where error occurred (1-indexed)
        column: Column number where error occurred (1-indexed)
        error_type: Category of error ('undefined_variable', 'undefined_property', etc.)
    """
    message: str
    line: int
    column: int
    error_type: str

    def __str__(self) -> str:
        """Format error for display."""
        return f"{self.error_type} at line {self.line}, column {self.column}: {self.message}"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"SemanticError(message={self.message!r}, line={self.line}, "
                f"column={self.column}, error_type={self.error_type!r})")
