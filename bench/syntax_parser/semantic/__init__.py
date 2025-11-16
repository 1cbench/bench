"""
Semantic analyzer for 1C language.

This package provides semantic analysis on top of the lexer and AST parser
to detect semantic errors that are syntactically valid but logically incorrect.
"""

from .semantic_analyzer import SemanticAnalyzer
from .errors import SemanticError
from .symbol_table import Symbol, SymbolTable

__all__ = [
    'SemanticAnalyzer',
    'SemanticError',
    'Symbol',
    'SymbolTable',
]
