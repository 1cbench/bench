"""
Main semantic analyzer for 1C language.

This module provides the SemanticAnalyzer class which coordinates
all semantic checks and returns a list of semantic errors.
"""

from typing import List, Optional, TYPE_CHECKING
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from syntax.parser.ast_nodes import ASTNode, ModuleNode
from .errors import SemanticError
from .symbol_table import SymbolTable
from .checkers.undefined_variable import VariableCollector, UndefinedVariableChecker

if TYPE_CHECKING:
    from .builtins.registry import BuiltinRegistry


class SemanticAnalyzer:
    """
    Main semantic analyzer for 1C code.

    Performs semantic analysis on an AST to detect:
    - Phase 1: Undefined variables and functions
    - Phase 1.5: Unknown types in 'Новый' expressions
    - Phase 2: Invalid property access (future)
    - Phase 3: Additional checks (future)
    """

    def __init__(self, builtins: Optional['BuiltinRegistry'] = None):
        """
        Initialize the semantic analyzer.

        Args:
            builtins: Optional BuiltinRegistry for 1C platform built-in functions and types.
                     If provided, built-in calls like НСтр(), ЗначениеЗаполнено() won't
                     be reported as undefined.
        """
        self.errors: List[SemanticError] = []
        self.symbol_table: SymbolTable = None
        self._builtins = builtins

    def analyze(self, ast: ASTNode) -> List[SemanticError]:
        """
        Analyze an AST and return all semantic errors found.

        Args:
            ast: Root AST node (typically ModuleNode)

        Returns:
            List of SemanticError objects found during analysis

        The analysis is performed in multiple passes:
        1. Variable collection pass - builds symbol table
        2. Undefined variable check pass - validates all variable references
        """
        self.errors = []

        if not isinstance(ast, ModuleNode):
            # If not a module node, we can't analyze it
            self.errors.append(
                SemanticError(
                    message="Expected ModuleNode as root of AST",
                    line=0,
                    column=0,
                    error_type='invalid_ast'
                )
            )
            return self.errors

        # Phase 1: Collect all variable declarations
        self._collect_variables(ast)

        # Phase 1: Check for undefined variables
        self._check_undefined_variables(ast)

        # Future phases will be added here:
        # - Phase 2: Property access validation
        # - Phase 3: Return path analysis, dead code detection, etc.

        return self.errors

    def _collect_variables(self, ast: ModuleNode):
        """
        First pass: Collect all variable declarations and build symbol table.

        Args:
            ast: Module AST node
        """
        collector = VariableCollector(builtins=self._builtins)
        collector.visit(ast)
        self.symbol_table = collector.symbol_table

    def _check_undefined_variables(self, ast: ModuleNode):
        """
        Second pass: Check all variable references against symbol table.

        Args:
            ast: Module AST node
        """
        checker = UndefinedVariableChecker(self.symbol_table)
        checker.visit(ast)
        self.errors.extend(checker.errors)

    def get_symbol_table(self) -> SymbolTable:
        """
        Get the symbol table created during analysis.

        Returns:
            SymbolTable object, or None if analyze() hasn't been called yet
        """
        return self.symbol_table

    def print_errors(self):
        """Print all errors to stdout in a human-readable format."""
        if not self.errors:
            print("No semantic errors found.")
            return

        print(f"Found {len(self.errors)} semantic error(s):\n")
        for error in self.errors:
            print(f"  {error}")

    def has_errors(self) -> bool:
        """
        Check if any errors were found during analysis.

        Returns:
            True if errors were found, False otherwise
        """
        return len(self.errors) > 0
