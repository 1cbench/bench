"""
Lexer implementation for 1C language.

This module provides the Lexer class that converts 1C source code
into a stream of tokens.
"""

from __future__ import annotations
from .token import Token, TokenType, KEYWORDS, KEYWORDS_LOWER, OPERATORS, DELIMITERS


class LexerError(Exception):
    """Exception raised when lexer encounters an error."""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Lexer error at {line}:{column}: {message}")


class Lexer:
    """
    Lexical analyzer for 1C language.

    Converts source code into a stream of tokens, handling:
    - Cyrillic keywords and identifiers
    - String literals (with quotes)
    - Number literals (integers and decimals)
    - Date literals
    - Comments (single-line with //)
    - Annotations (starting with &)
    - Preprocessor directives (starting with #)
    - Operators and delimiters
    """

    def __init__(self, source_code: str):
        """
        Initialize the lexer with source code.

        Args:
            source_code: 1C source code string to tokenize
        """
        # Strip BOM (Byte Order Mark) if present
        if source_code.startswith('\ufeff'):
            source_code = source_code[1:]
        self.source = source_code
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def current_char(self) -> str | None:
        """Get current character without advancing position."""
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset: int = 1) -> str | None:
        """Peek ahead at character at current position + offset."""
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]

    def advance(self) -> str | None:
        """
        Move to next character and return it.
        Updates line and column tracking.
        """
        if self.pos >= len(self.source):
            return None

        char = self.source[self.pos]
        self.pos += 1

        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def skip_whitespace(self):
        """Skip whitespace characters except newlines."""
        while self.current_char() and self.current_char() in ' \t\r':
            self.advance()

    def read_string(self) -> Token:
        """
        Read a string literal enclosed in double quotes.
        Supports escaped quotes ("").
        """
        start_line = self.line
        start_column = self.column

        # Skip opening quote
        self.advance()

        value = ''
        while self.current_char() is not None:
            char = self.current_char()

            if char == '"':
                # Check for escaped quote
                if self.peek_char() == '"':
                    value += '"'
                    self.advance()  # Skip first quote
                    self.advance()  # Skip second quote
                else:
                    # End of string
                    self.advance()  # Skip closing quote
                    return Token(TokenType.LITERAL_STRING, value, start_line, start_column)
            elif char == '\n':
                # Multi-line string support
                value += char
                self.advance()
            else:
                value += char
                self.advance()

        # Unterminated string
        raise LexerError("Unterminated string literal", start_line, start_column)

    def read_number(self) -> Token:
        """
        Read a number literal (integer or decimal).
        Supports formats: 123, 123.456, .456
        """
        start_line = self.line
        start_column = self.column

        value = ''
        has_dot = False

        while self.current_char() is not None:
            char = self.current_char()

            if char.isdigit():
                value += char
                self.advance()
            elif char == '.' and not has_dot and self.peek_char() and self.peek_char().isdigit():
                # Decimal point (only if followed by digit)
                has_dot = True
                value += char
                self.advance()
            else:
                break

        return Token(TokenType.LITERAL_NUMBER, value, start_line, start_column)

    def read_identifier_or_keyword(self) -> Token:
        """
        Read an identifier or keyword.
        1C identifiers can contain Cyrillic and Latin letters, digits, and underscores.
        """
        start_line = self.line
        start_column = self.column

        value = ''
        while self.current_char() is not None:
            char = self.current_char()

            # Check if character is valid for identifier
            if char.isalnum() or char == '_' or self._is_cyrillic(char):
                value += char
                self.advance()
            else:
                break

        # Check if it's a keyword (case-insensitive)
        # In 1C, keywords can be written in any case: "Перем", "перем", "ПЕРЕМ", "ПеРеМ", etc.
        value_lower = value.lower()
        if value_lower in KEYWORDS_LOWER:
            return Token(KEYWORDS_LOWER[value_lower], value, start_line, start_column)

        # Otherwise it's an identifier
        return Token(TokenType.IDENTIFIER, value, start_line, start_column)

    def read_comment(self) -> Token:
        """Read a single-line comment starting with //."""
        start_line = self.line
        start_column = self.column

        # Skip //
        self.advance()
        self.advance()

        value = ''
        while self.current_char() is not None and self.current_char() != '\n':
            value += self.current_char()
            self.advance()

        return Token(TokenType.COMMENT, value.strip(), start_line, start_column)

    def read_annotation(self) -> Token:
        """Read an annotation starting with & (e.g., &НаСервере, &НаКлиенте)."""
        start_line = self.line
        start_column = self.column

        # Skip &
        self.advance()

        value = '&'
        while self.current_char() is not None:
            char = self.current_char()

            if char.isalnum() or self._is_cyrillic(char):
                value += char
                self.advance()
            else:
                break

        return Token(TokenType.ANNOTATION, value, start_line, start_column)

    def read_preprocessor(self) -> Token:
        """Read a preprocessor directive starting with # (e.g., #Если, #КонецЕсли).

        Reads the entire line as the preprocessor content since preprocessor
        directives in 1C can contain conditions like:
        #Если Сервер Или ТолстыйКлиентОбычноеПриложение Тогда
        """
        start_line = self.line
        start_column = self.column

        # Read the entire preprocessor line (up to newline)
        value = ''
        while self.current_char() is not None and self.current_char() != '\n':
            value += self.current_char()
            self.advance()

        value = value.strip()

        # Check for known preprocessor directives (case insensitive check)
        value_lower = value.lower()
        if value_lower.startswith("#если"):
            return Token(TokenType.PREPROCESSOR_IF, value, start_line, start_column)
        elif value_lower.startswith("#конецесли"):
            return Token(TokenType.PREPROCESSOR_ENDIF, value, start_line, start_column)
        elif value_lower.startswith("#иначе"):
            return Token(TokenType.PREPROCESSOR_ELSE, value, start_line, start_column)
        elif value_lower.startswith("#область"):
            return Token(TokenType.PREPROCESSOR_IF, value, start_line, start_column)
        elif value_lower.startswith("#конецобласти"):
            return Token(TokenType.PREPROCESSOR_ENDIF, value, start_line, start_column)
        else:
            # Generic preprocessor directive
            return Token(TokenType.PREPROCESSOR_IF, value, start_line, start_column)

    def read_date(self) -> Token:
        """
        Read a date literal in format '00010101080000' or '20240115'.
        Date literals are enclosed in single quotes.
        """
        start_line = self.line
        start_column = self.column

        # Skip opening quote
        self.advance()

        value = ''
        while self.current_char() is not None:
            char = self.current_char()

            if char == "'":
                # End of date
                self.advance()
                return Token(TokenType.LITERAL_DATE, value, start_line, start_column)
            elif char.isdigit():
                value += char
                self.advance()
            else:
                # Invalid date format
                raise LexerError(f"Invalid date literal: unexpected character '{char}'",
                               self.line, self.column)

        raise LexerError("Unterminated date literal", start_line, start_column)

    def read_operator(self) -> Token | None:
        """
        Read an operator token.
        Handles multi-character operators like <=, >=, <>.
        """
        start_line = self.line
        start_column = self.column

        char = self.current_char()
        next_char = self.peek_char()

        # Check for two-character operators
        two_char = char + (next_char if next_char else '')
        if two_char in OPERATORS:
            self.advance()
            self.advance()
            return Token(OPERATORS[two_char], two_char, start_line, start_column)

        # Check for single-character operators
        if char in OPERATORS:
            self.advance()
            return Token(OPERATORS[char], char, start_line, start_column)

        return None

    def _is_cyrillic(self, char: str) -> bool:
        """Check if character is a Cyrillic letter."""
        if not char:
            return False
        code = ord(char)
        # Cyrillic Unicode ranges: 0x0400-0x04FF (Cyrillic), 0x0500-0x052F (Cyrillic Supplement)
        return (0x0400 <= code <= 0x04FF) or (0x0500 <= code <= 0x052F)

    def tokenize(self) -> list[Token]:
        """
        Main tokenization method.

        Returns:
            List of tokens extracted from source code.

        Raises:
            LexerError: If invalid syntax is encountered.
        """
        self.tokens = []

        while self.pos < len(self.source):
            self.skip_whitespace()

            char = self.current_char()

            if char is None:
                break

            # Handle newlines
            if char == '\n':
                token = Token(TokenType.NEWLINE, '\\n', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue

            # Handle comments
            if char == '/' and self.peek_char() == '/':
                token = self.read_comment()
                self.tokens.append(token)
                continue

            # Handle string literals
            if char == '"':
                token = self.read_string()
                self.tokens.append(token)
                continue

            # Handle date literals
            if char == "'":
                token = self.read_date()
                self.tokens.append(token)
                continue

            # Handle annotations
            if char == '&':
                token = self.read_annotation()
                self.tokens.append(token)
                continue

            # Handle preprocessor directives
            if char == '#':
                token = self.read_preprocessor()
                self.tokens.append(token)
                continue

            # Handle numbers
            if char.isdigit():
                token = self.read_number()
                self.tokens.append(token)
                continue

            # Handle identifiers and keywords
            if char.isalpha() or char == '_' or self._is_cyrillic(char):
                token = self.read_identifier_or_keyword()
                self.tokens.append(token)
                continue

            # Handle delimiters
            if char in DELIMITERS:
                token = Token(DELIMITERS[char], char, self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue

            # Handle operators
            op_token = self.read_operator()
            if op_token:
                self.tokens.append(op_token)
                continue

            # Unknown character
            raise LexerError(f"Unexpected character: '{char}'", self.line, self.column)

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))

        return self.tokens

    def tokenize_without_whitespace(self) -> list[Token]:
        """
        Tokenize and filter out newline and comment tokens.
        Useful for parsers that don't need to preserve formatting.
        """
        all_tokens = self.tokenize()
        return [
            token for token in all_tokens
            if token.type not in (TokenType.NEWLINE, TokenType.COMMENT)
        ]
