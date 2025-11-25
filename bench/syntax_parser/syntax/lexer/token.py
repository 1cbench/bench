"""
Token classes and types for 1C language lexer.
"""

from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Enumeration of all token types in 1C language."""

    # Keywords - Procedure/Function
    KEYWORD_PROCEDURE = "Процедура"
    KEYWORD_FUNCTION = "Функция"
    KEYWORD_END_PROCEDURE = "КонецПроцедуры"
    KEYWORD_END_FUNCTION = "КонецФункции"

    # Keywords - Control Flow
    KEYWORD_IF = "Если"
    KEYWORD_THEN = "Тогда"
    KEYWORD_ELSE = "Иначе"
    KEYWORD_ELSE_IF = "ИначеЕсли"
    KEYWORD_END_IF = "КонецЕсли"
    KEYWORD_FOR = "Для"
    KEYWORD_EACH = "Каждого"
    KEYWORD_FROM = "Из"
    KEYWORD_CYCLE = "Цикл"
    KEYWORD_END_CYCLE = "КонецЦикла"
    KEYWORD_WHILE = "Пока"
    KEYWORD_TO = "По"
    KEYWORD_TRY = "Попытка"
    KEYWORD_EXCEPTION = "Исключение"
    KEYWORD_END_TRY = "КонецПопытки"
    KEYWORD_BREAK = "Прервать"
    KEYWORD_CONTINUE = "Продолжить"
    KEYWORD_RAISE = "ВызватьИсключение"

    # Keywords - Variables and Objects
    KEYWORD_VAR = "Перем"
    KEYWORD_VAL = "Знач"
    KEYWORD_NEW = "Новый"
    KEYWORD_RETURN = "Возврат"
    KEYWORD_EXPORT = "Экспорт"

    # Keywords - Async
    KEYWORD_ASYNC = "Асинх"
    KEYWORD_AWAIT = "Ждать"

    # Keywords - Logical Operators
    KEYWORD_AND = "И"
    KEYWORD_OR = "ИЛИ"
    KEYWORD_NOT = "НЕ"

    # Keywords - Literals
    KEYWORD_TRUE = "Истина"
    KEYWORD_FALSE = "Ложь"
    KEYWORD_UNDEFINED = "Неопределено"

    # Operators - Arithmetic
    OP_PLUS = "+"
    OP_MINUS = "-"
    OP_MULTIPLY = "*"
    OP_DIVIDE = "/"
    OP_MODULO = "%"

    # Operators - Comparison
    OP_ASSIGN = "="
    OP_EQUALS = "="
    OP_NOT_EQUALS = "<>"
    OP_LESS = "<"
    OP_GREATER = ">"
    OP_LESS_EQUAL = "<="
    OP_GREATER_EQUAL = ">="

    # Operators - Ternary
    OP_TERNARY = "?"

    # Delimiters
    DELIMITER_SEMICOLON = ";"
    DELIMITER_COMMA = ","
    DELIMITER_DOT = "."
    DELIMITER_LPAREN = "("
    DELIMITER_RPAREN = ")"
    DELIMITER_LBRACKET = "["
    DELIMITER_RBRACKET = "]"
    DELIMITER_PIPE = "|"

    # Literals
    LITERAL_STRING = "STRING"
    LITERAL_NUMBER = "NUMBER"
    LITERAL_DATE = "DATE"

    # Identifiers
    IDENTIFIER = "IDENTIFIER"

    # Annotations/Decorators
    ANNOTATION = "ANNOTATION"

    # Preprocessor
    PREPROCESSOR_IF = "#Если"
    PREPROCESSOR_ELSE = "#Иначе"
    PREPROCESSOR_ENDIF = "#КонецЕсли"

    # Special
    COMMENT = "COMMENT"
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    WHITESPACE = "WHITESPACE"


@dataclass
class Token:
    """
    Represents a single token from the source code.

    Attributes:
        type: The type of the token
        value: The string value of the token
        line: Line number where the token appears (1-indexed)
        column: Column number where the token starts (1-indexed)
    """
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"

    def is_keyword(self) -> bool:
        """Check if this token is a keyword."""
        return self.type.name.startswith("KEYWORD_")

    def is_operator(self) -> bool:
        """Check if this token is an operator."""
        return self.type.name.startswith("OP_")

    def is_delimiter(self) -> bool:
        """Check if this token is a delimiter."""
        return self.type.name.startswith("DELIMITER_")

    def is_literal(self) -> bool:
        """Check if this token is a literal value."""
        return self.type.name.startswith("LITERAL_")


# Map of keyword strings to their token types
KEYWORDS = {
    "Процедура": TokenType.KEYWORD_PROCEDURE,
    "Функция": TokenType.KEYWORD_FUNCTION,
    "КонецПроцедуры": TokenType.KEYWORD_END_PROCEDURE,
    "КонецФункции": TokenType.KEYWORD_END_FUNCTION,
    "Если": TokenType.KEYWORD_IF,
    "Тогда": TokenType.KEYWORD_THEN,
    "Иначе": TokenType.KEYWORD_ELSE,
    "ИначеЕсли": TokenType.KEYWORD_ELSE_IF,
    "КонецЕсли": TokenType.KEYWORD_END_IF,
    "Для": TokenType.KEYWORD_FOR,
    "Каждого": TokenType.KEYWORD_EACH,
    "Из": TokenType.KEYWORD_FROM,
    "Цикл": TokenType.KEYWORD_CYCLE,
    "КонецЦикла": TokenType.KEYWORD_END_CYCLE,
    "Пока": TokenType.KEYWORD_WHILE,
    "По": TokenType.KEYWORD_TO,
    "Перем": TokenType.KEYWORD_VAR,
    "Знач": TokenType.KEYWORD_VAL,
    "Новый": TokenType.KEYWORD_NEW,
    "Возврат": TokenType.KEYWORD_RETURN,
    "Экспорт": TokenType.KEYWORD_EXPORT,
    "Попытка": TokenType.KEYWORD_TRY,
    "Исключение": TokenType.KEYWORD_EXCEPTION,
    "КонецПопытки": TokenType.KEYWORD_END_TRY,
    "Прервать": TokenType.KEYWORD_BREAK,
    "Продолжить": TokenType.KEYWORD_CONTINUE,
    "ВызватьИсключение": TokenType.KEYWORD_RAISE,
    "Асинх": TokenType.KEYWORD_ASYNC,
    "Ждать": TokenType.KEYWORD_AWAIT,
    "И": TokenType.KEYWORD_AND,
    "ИЛИ": TokenType.KEYWORD_OR,
    "НЕ": TokenType.KEYWORD_NOT,
    "Истина": TokenType.KEYWORD_TRUE,
    "Ложь": TokenType.KEYWORD_FALSE,
    "Неопределено": TokenType.KEYWORD_UNDEFINED,
}

# Case-insensitive keyword lookup
# In 1C, keywords can be written in any case: "Перем", "перем", "ПЕРЕМ", "ПеРеМ", etc.
KEYWORDS_LOWER = {k.lower(): v for k, v in KEYWORDS.items()}


# Mapping of operators to their token types
OPERATORS = {
    "+": TokenType.OP_PLUS,
    "-": TokenType.OP_MINUS,
    "*": TokenType.OP_MULTIPLY,
    "/": TokenType.OP_DIVIDE,
    "%": TokenType.OP_MODULO,
    "=": TokenType.OP_ASSIGN,
    "<>": TokenType.OP_NOT_EQUALS,
    "<": TokenType.OP_LESS,
    ">": TokenType.OP_GREATER,
    "<=": TokenType.OP_LESS_EQUAL,
    ">=": TokenType.OP_GREATER_EQUAL,
    "?": TokenType.OP_TERNARY,
}


# Mapping of delimiters to their token types
DELIMITERS = {
    ";": TokenType.DELIMITER_SEMICOLON,
    ",": TokenType.DELIMITER_COMMA,
    ".": TokenType.DELIMITER_DOT,
    "(": TokenType.DELIMITER_LPAREN,
    ")": TokenType.DELIMITER_RPAREN,
    "[": TokenType.DELIMITER_LBRACKET,
    "]": TokenType.DELIMITER_RBRACKET,
    "|": TokenType.DELIMITER_PIPE,
}
