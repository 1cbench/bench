"""
Basic tests to verify project setup is correct.
"""

import pytest
from syntax_parser.lexer import Token, TokenType
from syntax_parser.parser import ASTNode, ModuleNode, IdentifierNode
from syntax_parser.type_system import Type, PrimitiveType, NUMBER_TYPE, STRING_TYPE
from syntax_parser.errors import Error, ErrorReporter


class TestTokenSetup:
    """Test that token classes are properly set up."""

    def test_token_creation(self):
        """Test creating a basic token."""
        token = Token(TokenType.KEYWORD_FUNCTION, "Функция", 1, 5)
        assert token.type == TokenType.KEYWORD_FUNCTION
        assert token.value == "Функция"
        assert token.line == 1
        assert token.column == 5

    def test_token_is_keyword(self):
        """Test token type checking methods."""
        keyword_token = Token(TokenType.KEYWORD_IF, "Если", 1, 1)
        assert keyword_token.is_keyword()
        assert not keyword_token.is_operator()
        assert not keyword_token.is_delimiter()

    def test_token_is_operator(self):
        """Test operator token type checking."""
        op_token = Token(TokenType.OP_PLUS, "+", 1, 1)
        assert op_token.is_operator()
        assert not op_token.is_keyword()


class TestASTNodeSetup:
    """Test that AST node classes are properly set up."""

    def test_module_node_creation(self):
        """Test creating a module node."""
        module = ModuleNode(line=1, column=1)
        assert module.line == 1
        assert module.column == 1
        assert module.functions == []
        assert module.procedures == []

    def test_identifier_node_creation(self):
        """Test creating an identifier node."""
        identifier = IdentifierNode(name="МояПеременная", line=5, column=10)
        assert identifier.name == "МояПеременная"
        assert identifier.line == 5
        assert identifier.column == 10


class TestTypeSystemSetup:
    """Test that type system is properly set up."""

    def test_primitive_type_creation(self):
        """Test creating primitive types."""
        num_type = PrimitiveType("Число")
        assert num_type.name == "Число"

    def test_predefined_types(self):
        """Test that predefined types are available."""
        assert NUMBER_TYPE.name == "Число"
        assert STRING_TYPE.name == "Строка"

    def test_type_equality(self):
        """Test type equality comparison."""
        type1 = PrimitiveType("Число")
        type2 = PrimitiveType("Число")
        type3 = PrimitiveType("Строка")

        assert type1 == type2
        assert type1 != type3

    def test_type_compatibility(self):
        """Test basic type compatibility."""
        num_type = PrimitiveType("Число")
        str_type = PrimitiveType("Строка")

        # Same types are compatible
        assert num_type.is_compatible_with(num_type)

        # Different types are not compatible
        assert not num_type.is_compatible_with(str_type)


class TestErrorReporterSetup:
    """Test that error reporting is properly set up."""

    def test_error_creation(self):
        """Test creating an error."""
        error = Error("Test error message", 10, 5, "syntax")
        assert error.message == "Test error message"
        assert error.line == 10
        assert error.column == 5
        assert error.error_type == "syntax"

    def test_error_reporter_add_error(self):
        """Test adding errors to reporter."""
        reporter = ErrorReporter()
        assert not reporter.has_errors()
        assert reporter.error_count() == 0

        reporter.add_error("First error", 1, 1, "syntax")
        assert reporter.has_errors()
        assert reporter.error_count() == 1

        reporter.add_type_error("Type mismatch", 5, 10)
        assert reporter.error_count() == 2

    def test_error_reporter_format(self):
        """Test error formatting."""
        reporter = ErrorReporter()
        reporter.add_syntax_error("Syntax error", 1, 5)
        reporter.add_type_error("Type error", 3, 10)

        formatted = reporter.format_errors()
        assert "SYNTAX" in formatted
        assert "TYPE" in formatted
        assert "Line 1:5" in formatted
        assert "Line 3:10" in formatted

    def test_error_reporter_clear(self):
        """Test clearing errors."""
        reporter = ErrorReporter()
        reporter.add_error("Error 1", 1, 1)
        reporter.add_error("Error 2", 2, 2)
        assert reporter.error_count() == 2

        reporter.clear()
        assert reporter.error_count() == 0
        assert not reporter.has_errors()


class TestProjectStructure:
    """Test that project structure is correctly set up."""

    def test_imports_work(self):
        """Test that all main imports work."""
        # This test passes if all imports at the top of the file work
        assert Token is not None
        assert TokenType is not None
        assert ASTNode is not None
        assert Type is not None
        assert Error is not None
        assert ErrorReporter is not None

    def test_version_available(self):
        """Test that package version is available."""
        import syntax_parser
        assert hasattr(syntax_parser, '__version__')
        assert syntax_parser.__version__ == "0.1.0"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
