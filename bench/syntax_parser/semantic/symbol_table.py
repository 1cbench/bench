"""
Symbol table implementation for tracking variable scopes in 1C code.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Symbol:
    """
    Represents a symbol (variable, parameter, function, etc.) in the symbol table.

    Attributes:
        name: Symbol name
        kind: Symbol kind ('parameter', 'variable', 'function', 'procedure')
        line: Line number where symbol is declared (1-indexed)
        column: Column number where symbol is declared (1-indexed)
        scope_level: Nesting level of the scope (0 = module level, 1 = function level, etc.)
    """
    name: str
    kind: str  # 'parameter', 'variable', 'function', 'procedure', 'loop_variable'
    line: int
    column: int
    scope_level: int

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Symbol(name={self.name!r}, kind={self.kind!r}, "
                f"line={self.line}, column={self.column}, scope_level={self.scope_level})")


class SymbolTable:
    """
    Symbol table for managing variable scopes.

    Uses a stack-based approach where each scope is a dictionary mapping
    symbol names to Symbol objects. Supports nested scopes for module,
    function/procedure, and nested blocks.
    """

    def __init__(self):
        """Initialize with a single module-level scope."""
        self.scopes: list[dict[str, Symbol]] = [{}]  # Stack of scopes
        self.current_scope_level = 0

    def enter_scope(self):
        """
        Enter a new scope (push a new scope onto the stack).

        Called when entering functions, procedures, or blocks.
        """
        self.scopes.append({})
        self.current_scope_level += 1

    def exit_scope(self):
        """
        Exit the current scope (pop scope from the stack).

        Called when leaving functions, procedures, or blocks.
        """
        if len(self.scopes) > 1:  # Never pop the module-level scope
            self.scopes.pop()
            self.current_scope_level -= 1

    def define(self, name: str, symbol: Symbol):
        """
        Add a symbol to the current scope.

        Args:
            name: Symbol name (case-insensitive in 1C)
            symbol: Symbol object to add

        Note: In 1C, identifiers are case-insensitive, so we normalize to lowercase.
        """
        normalized_name = name.lower()
        self.scopes[-1][normalized_name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol in current scope and all parent scopes.

        Args:
            name: Symbol name to look up (case-insensitive)

        Returns:
            Symbol object if found, None otherwise
        """
        normalized_name = name.lower()

        # Search from innermost to outermost scope
        for scope in reversed(self.scopes):
            if normalized_name in scope:
                return scope[normalized_name]

        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol in the current scope only (not parent scopes).

        Args:
            name: Symbol name to look up (case-insensitive)

        Returns:
            Symbol object if found in current scope, None otherwise
        """
        normalized_name = name.lower()
        return self.scopes[-1].get(normalized_name)

    def is_defined(self, name: str) -> bool:
        """
        Check if a symbol is defined in current or parent scopes.

        Args:
            name: Symbol name to check (case-insensitive)

        Returns:
            True if symbol is defined, False otherwise
        """
        return self.lookup(name) is not None

    def get_current_scope_level(self) -> int:
        """
        Get the current scope nesting level.

        Returns:
            Current scope level (0 = module level, 1+ = nested scopes)
        """
        return self.current_scope_level

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"SymbolTable(scopes={self.scopes}, level={self.current_scope_level})"
