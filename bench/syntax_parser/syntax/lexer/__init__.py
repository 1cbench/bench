"""
Lexical analyzer (tokenizer) for 1C language.
"""

from .token import Token, TokenType, KEYWORDS, KEYWORDS_LOWER, OPERATORS, DELIMITERS
from .lexer import Lexer, LexerError

__all__ = [
    "Token",
    "TokenType",
    "KEYWORDS",
    "KEYWORDS_LOWER",
    "OPERATORS",
    "DELIMITERS",
    "Lexer",
    "LexerError",
]
