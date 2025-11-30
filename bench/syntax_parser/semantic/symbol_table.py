"""
Symbol table implementation for tracking variable scopes in 1C code.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .builtins.registry import BuiltinRegistry


@dataclass
class Symbol:
    """
    Represents a symbol (variable, parameter, function, etc.) in the symbol table.

    Attributes:
        name: Symbol name
        kind: Symbol kind ('parameter', 'variable', 'function', 'procedure',
              'builtin_function', 'builtin_type')
        line: Line number where symbol is declared (1-indexed, 0 for builtins)
        column: Column number where symbol is declared (1-indexed, 0 for builtins)
        scope_level: Nesting level of the scope (0 = module level, 1 = function level, etc.)
        is_builtin: Whether this is a built-in 1C symbol
    """
    name: str
    kind: str  # 'parameter', 'variable', 'function', 'procedure', 'loop_variable', 'builtin_function', 'builtin_type'
    line: int
    column: int
    scope_level: int
    is_builtin: bool = False

    def __repr__(self) -> str:
        """String representation for debugging."""
        builtin_str = ", builtin=True" if self.is_builtin else ""
        return (f"Symbol(name={self.name!r}, kind={self.kind!r}, "
                f"line={self.line}, column={self.column}, scope_level={self.scope_level}{builtin_str})")


class SymbolTable:
    """
    Symbol table for managing variable scopes.

    Uses a stack-based approach where each scope is a dictionary mapping
    symbol names to Symbol objects. Supports nested scopes for module,
    function/procedure, and nested blocks.
    """

    def __init__(self, builtins: 'BuiltinRegistry' = None):
        """
        Initialize with a single module-level scope.

        Args:
            builtins: Optional BuiltinRegistry to pre-populate with built-in functions and types
        """
        self.scopes: list[dict[str, Symbol]] = [{}]  # Stack of scopes
        self.current_scope_level = 0
        self._builtins_count = 0

        # Pre-populate with built-in functions and types if provided
        if builtins is not None:
            self._populate_builtins(builtins)

    def _populate_builtins(self, builtins: 'BuiltinRegistry'):
        """
        Pre-populate the module scope with built-in functions and types.

        Args:
            builtins: BuiltinRegistry containing 1C platform built-ins
        """
        # Add built-in functions
        for func_name in builtins.get_all_functions():
            info = builtins.get_function_info(func_name)
            if info:
                self.scopes[0][func_name] = Symbol(
                    name=info.name_ru or func_name,
                    kind='builtin_function',
                    line=0,
                    column=0,
                    scope_level=0,
                    is_builtin=True
                )
                self._builtins_count += 1

        # Add built-in types
        for type_name in builtins.get_all_types():
            info = builtins.get_type_info(type_name)
            if info:
                self.scopes[0][type_name] = Symbol(
                    name=info.name_ru or type_name,
                    kind='builtin_type',
                    line=0,
                    column=0,
                    scope_level=0,
                    is_builtin=True
                )
                self._builtins_count += 1

    def get_builtins_count(self) -> int:
        """Return the number of built-in symbols loaded."""
        return self._builtins_count

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
