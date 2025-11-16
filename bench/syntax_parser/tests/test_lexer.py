"""
Unit tests for the 1C lexer.
"""

import pytest
from syntax_parser.lexer import Lexer, LexerError, TokenType


class TestBasicTokenization:
    """Test basic tokenization functionality."""

    def test_empty_source(self):
        """Test tokenizing empty source."""
        lexer = Lexer("")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_variable_declaration(self):
        """Test tokenizing variable declaration."""
        code = "Перем МояПеременная;"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert len(tokens) == 4  # Перем, МояПеременная, ;, EOF
        assert tokens[0].type == TokenType.KEYWORD_VAR
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "МояПеременная"
        assert tokens[2].type == TokenType.DELIMITER_SEMICOLON

    def test_multiple_variables(self):
        """Test tokenizing multiple variable declarations."""
        code = "Перем А, Б, В;"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_VAR
        assert tokens[1].value == "А"
        assert tokens[2].type == TokenType.DELIMITER_COMMA
        assert tokens[3].value == "Б"
        assert tokens[4].type == TokenType.DELIMITER_COMMA
        assert tokens[5].value == "В"


class TestKeywords:
    """Test keyword recognition."""

    def test_function_keywords(self):
        """Test function-related keywords."""
        code = "Функция Тест() КонецФункции"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_FUNCTION
        # tokens: Функция, Тест, (, ), КонецФункции, EOF
        assert tokens[4].type == TokenType.KEYWORD_END_FUNCTION

    def test_procedure_keywords(self):
        """Test procedure-related keywords."""
        code = "Процедура Тест() КонецПроцедуры"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_PROCEDURE
        # tokens: Процедура, Тест, (, ), КонецПроцедуры, EOF
        assert tokens[4].type == TokenType.KEYWORD_END_PROCEDURE

    def test_control_flow_keywords(self):
        """Test control flow keywords."""
        code = "Если Тогда Иначе КонецЕсли"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_IF
        assert tokens[1].type == TokenType.KEYWORD_THEN
        assert tokens[2].type == TokenType.KEYWORD_ELSE
        assert tokens[3].type == TokenType.KEYWORD_END_IF

    def test_loop_keywords(self):
        """Test loop keywords."""
        code = "Для По Цикл КонецЦикла Пока"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_FOR
        assert tokens[1].type == TokenType.KEYWORD_TO
        assert tokens[2].type == TokenType.KEYWORD_CYCLE
        assert tokens[3].type == TokenType.KEYWORD_END_CYCLE
        assert tokens[4].type == TokenType.KEYWORD_WHILE

    def test_logical_operators(self):
        """Test logical operator keywords."""
        code = "И ИЛИ НЕ"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_AND
        assert tokens[1].type == TokenType.KEYWORD_OR
        assert tokens[2].type == TokenType.KEYWORD_NOT

    def test_boolean_literals(self):
        """Test boolean literal keywords."""
        code = "Истина Ложь Неопределено"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.KEYWORD_TRUE
        assert tokens[1].type == TokenType.KEYWORD_FALSE
        assert tokens[2].type == TokenType.KEYWORD_UNDEFINED


class TestOperators:
    """Test operator tokenization."""

    def test_arithmetic_operators(self):
        """Test arithmetic operators."""
        code = "+ - * / %"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.OP_PLUS
        assert tokens[1].type == TokenType.OP_MINUS
        assert tokens[2].type == TokenType.OP_MULTIPLY
        assert tokens[3].type == TokenType.OP_DIVIDE
        assert tokens[4].type == TokenType.OP_MODULO

    def test_comparison_operators(self):
        """Test comparison operators."""
        code = "= <> < > <= >="
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.OP_ASSIGN
        assert tokens[1].type == TokenType.OP_NOT_EQUALS
        assert tokens[2].type == TokenType.OP_LESS
        assert tokens[3].type == TokenType.OP_GREATER
        assert tokens[4].type == TokenType.OP_LESS_EQUAL
        assert tokens[5].type == TokenType.OP_GREATER_EQUAL


class TestLiterals:
    """Test literal value tokenization."""

    def test_string_literal(self):
        """Test simple string literal."""
        code = '"Привет, мир!"'
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.LITERAL_STRING
        assert tokens[0].value == "Привет, мир!"

    def test_empty_string(self):
        """Test empty string literal."""
        code = '""'
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.LITERAL_STRING
        assert tokens[0].value == ""

    def test_string_with_escaped_quotes(self):
        """Test string with escaped quotes."""
        code = '"Он сказал: ""Привет"""'
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.LITERAL_STRING
        assert tokens[0].value == 'Он сказал: "Привет"'

    def test_integer_literal(self):
        """Test integer literal."""
        code = "12345"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.LITERAL_NUMBER
        assert tokens[0].value == "12345"

    def test_decimal_literal(self):
        """Test decimal literal."""
        code = "123.456"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.LITERAL_NUMBER
        assert tokens[0].value == "123.456"

    def test_date_literal(self):
        """Test date literal."""
        code = "'20240115'"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.LITERAL_DATE
        assert tokens[0].value == "20240115"


class TestComments:
    """Test comment handling."""

    def test_single_line_comment(self):
        """Test single-line comment."""
        code = "// Это комментарий"
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comment_tokens) == 1
        assert comment_tokens[0].value == "Это комментарий"

    def test_code_with_comment(self):
        """Test code with inline comment."""
        code = "Перем А; // Переменная А"
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        # Should have: Перем, А, ;, comment, EOF
        assert any(t.type == TokenType.KEYWORD_VAR for t in tokens)
        assert any(t.type == TokenType.COMMENT for t in tokens)


class TestAnnotations:
    """Test annotation/decorator handling."""

    def test_server_annotation(self):
        """Test server annotation."""
        code = "&НаСервере"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.ANNOTATION
        assert tokens[0].value == "&НаСервере"

    def test_client_annotation(self):
        """Test client annotation."""
        code = "&НаКлиенте"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.ANNOTATION
        assert tokens[0].value == "&НаКлиенте"


class TestComplexExpressions:
    """Test complex expression tokenization."""

    def test_arithmetic_expression(self):
        """Test arithmetic expression."""
        code = "Результат = (10 + 20) * 3;"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        # Should tokenize all parts correctly
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[1].type == TokenType.OP_ASSIGN
        assert tokens[2].type == TokenType.DELIMITER_LPAREN
        assert tokens[3].type == TokenType.LITERAL_NUMBER
        assert tokens[3].value == "10"

    def test_function_call(self):
        """Test function call."""
        code = "Результат = МояФункция(Параметр1, Параметр2);"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        # Find the identifier for function name
        func_tokens = [t for t in tokens if t.type == TokenType.IDENTIFIER and t.value == "МояФункция"]
        assert len(func_tokens) == 1

    def test_member_access(self):
        """Test member access."""
        code = "Объект.Свойство"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[1].type == TokenType.DELIMITER_DOT
        assert tokens[2].type == TokenType.IDENTIFIER


class TestErrors:
    """Test error handling."""

    def test_unterminated_string(self):
        """Test unterminated string error."""
        code = '"Незакрытая строка'
        lexer = Lexer(code)

        with pytest.raises(LexerError) as exc_info:
            lexer.tokenize()

        assert "Unterminated string" in str(exc_info.value)

    def test_unexpected_character(self):
        """Test unexpected character error."""
        code = "Перем А @ Б;"
        lexer = Lexer(code)

        with pytest.raises(LexerError) as exc_info:
            lexer.tokenize()

        assert "Unexpected character" in str(exc_info.value)


class TestPositionTracking:
    """Test line and column tracking."""

    def test_line_tracking(self):
        """Test line number tracking."""
        code = "Перем А;\nПерем Б;\nПерем В;"
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        # Find tokens on different lines
        tokens_no_newline = [t for t in tokens if t.type != TokenType.NEWLINE and t.type != TokenType.EOF]
        assert tokens_no_newline[0].line == 1  # First Перем
        assert tokens_no_newline[3].line == 2  # Second Перем
        assert tokens_no_newline[6].line == 3  # Third Перем

    def test_column_tracking(self):
        """Test column number tracking."""
        code = "Перем Переменная;"
        lexer = Lexer(code)
        tokens = lexer.tokenize_without_whitespace()

        assert tokens[0].column == 1  # Перем starts at column 1
        assert tokens[1].column == 7  # Переменная starts after "Перем "
