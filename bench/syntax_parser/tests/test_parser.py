"""
Unit tests for the 1C parser.
"""

import pytest
from syntax_parser.lexer import Lexer
from syntax_parser.parser import Parser, ParserError
from syntax_parser.parser import (
    ModuleNode,
    VarDeclarationNode,
    FunctionNode,
    ProcedureNode,
    AssignmentNode,
    IfNode,
    WhileNode,
    ForNode,
    ForEachNode,
    TryNode,
    ReturnNode,
    BinaryOpNode,
    UnaryOpNode,
    CallNode,
    MemberAccessNode,
    NewNode,
    IdentifierNode,
    LiteralNode,
    ExpressionStatementNode,
)


def parse(code: str) -> ModuleNode:
    """Helper to parse code and return AST."""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


class TestBasicParsing:
    """Test basic parsing functionality."""

    def test_empty_module(self):
        """Test parsing empty module."""
        ast = parse("")
        assert isinstance(ast, ModuleNode)
        assert len(ast.var_declarations) == 0
        assert len(ast.functions) == 0
        assert len(ast.procedures) == 0

    def test_variable_declaration_single(self):
        """Test single variable declaration."""
        ast = parse("Перем МояПеременная;")
        assert len(ast.var_declarations) == 1
        assert ast.var_declarations[0].names == ["МояПеременная"]

    def test_variable_declaration_multiple(self):
        """Test multiple variable declaration."""
        ast = parse("Перем А, Б, В;")
        assert len(ast.var_declarations) == 1
        assert ast.var_declarations[0].names == ["А", "Б", "В"]

    def test_multiple_variable_declarations(self):
        """Test multiple variable declaration statements."""
        code = """
        Перем А;
        Перем Б, В;
        """
        ast = parse(code)
        assert len(ast.var_declarations) == 2
        assert ast.var_declarations[0].names == ["А"]
        assert ast.var_declarations[1].names == ["Б", "В"]


class TestFunctions:
    """Test function parsing."""

    def test_empty_function(self):
        """Test empty function."""
        code = """
        Функция Тест()
        КонецФункции
        """
        ast = parse(code)
        assert len(ast.functions) == 1
        func = ast.functions[0]
        assert func.name == "Тест"
        assert len(func.parameters) == 0
        assert len(func.body) == 0
        assert not func.is_export
        assert not func.is_async

    def test_function_with_parameters(self):
        """Test function with parameters."""
        code = """
        Функция Сложить(А, Б, В)
        КонецФункции
        """
        ast = parse(code)
        func = ast.functions[0]
        assert func.name == "Сложить"
        assert len(func.parameters) == 3
        assert func.parameters[0].name == "А"
        assert func.parameters[1].name == "Б"
        assert func.parameters[2].name == "В"

    def test_function_with_export(self):
        """Test exported function."""
        code = """
        Функция Тест() Экспорт
        КонецФункции
        """
        ast = parse(code)
        assert ast.functions[0].is_export

    def test_async_function(self):
        """Test async function."""
        code = """
        Асинх Функция Тест()
        КонецФункции
        """
        ast = parse(code)
        assert ast.functions[0].is_async

    def test_function_with_annotation(self):
        """Test function with annotation."""
        code = """
        &НаСервере
        Функция Тест()
        КонецФункции
        """
        ast = parse(code)
        assert ast.functions[0].annotation == "&НаСервере"

    def test_function_with_body(self):
        """Test function with body."""
        code = """
        Функция Тест()
            Перем А;
            Возврат А;
        КонецФункции
        """
        ast = parse(code)
        func = ast.functions[0]
        assert len(func.body) == 2
        assert isinstance(func.body[0], VarDeclarationNode)
        assert isinstance(func.body[1], ReturnNode)


class TestProcedures:
    """Test procedure parsing."""

    def test_simple_procedure(self):
        """Test simple procedure."""
        code = """
        Процедура Тест()
        КонецПроцедуры
        """
        ast = parse(code)
        assert len(ast.procedures) == 1
        proc = ast.procedures[0]
        assert proc.name == "Тест"

    def test_procedure_with_export(self):
        """Test exported procedure."""
        code = """
        Процедура Тест() Экспорт
        КонецПроцедуры
        """
        ast = parse(code)
        assert ast.procedures[0].is_export


class TestStatements:
    """Test statement parsing."""

    def test_assignment(self):
        """Test assignment statement."""
        code = """
        Функция Тест()
            А = 10;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, AssignmentNode)
        assert isinstance(stmt.target, IdentifierNode)
        assert stmt.target.name == "А"
        assert isinstance(stmt.value, LiteralNode)
        assert stmt.value.value == 10

    def test_return_with_value(self):
        """Test return statement with value."""
        code = """
        Функция Тест()
            Возврат 42;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, ReturnNode)
        assert isinstance(stmt.value, LiteralNode)
        assert stmt.value.value == 42

    def test_return_without_value(self):
        """Test return statement without value."""
        code = """
        Функция Тест()
            Возврат;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, ReturnNode)
        assert stmt.value is None

    def test_expression_statement(self):
        """Test expression statement (function call)."""
        code = """
        Функция Тест()
            Сообщить("Привет");
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, ExpressionStatementNode)
        assert isinstance(stmt.expression, CallNode)


class TestIfStatement:
    """Test if statement parsing."""

    def test_simple_if(self):
        """Test simple if statement."""
        code = """
        Функция Тест()
            Если А Тогда
                Возврат 1;
            КонецЕсли;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, IfNode)
        assert isinstance(stmt.condition, IdentifierNode)
        assert len(stmt.then_body) == 1
        assert len(stmt.elif_branches) == 0
        assert stmt.else_body is None

    def test_if_with_else(self):
        """Test if-else statement."""
        code = """
        Функция Тест()
            Если А Тогда
                Возврат 1;
            Иначе
                Возврат 2;
            КонецЕсли;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, IfNode)
        assert stmt.else_body is not None
        assert len(stmt.else_body) == 1

    def test_if_with_elif(self):
        """Test if-elseif statement."""
        code = """
        Функция Тест()
            Если А Тогда
                Возврат 1;
            ИначеЕсли Б Тогда
                Возврат 2;
            КонецЕсли;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, IfNode)
        assert len(stmt.elif_branches) == 1
        assert isinstance(stmt.elif_branches[0][0], IdentifierNode)  # condition
        assert len(stmt.elif_branches[0][1]) == 1  # body


class TestLoops:
    """Test loop parsing."""

    def test_while_loop(self):
        """Test while loop."""
        code = """
        Функция Тест()
            Пока А Цикл
                Б = Б + 1;
            КонецЦикла;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, WhileNode)
        assert isinstance(stmt.condition, IdentifierNode)
        assert len(stmt.body) == 1

    def test_for_loop(self):
        """Test numeric for loop."""
        code = """
        Функция Тест()
            Для Счетчик = 1 По 10 Цикл
                Сообщить(Счетчик);
            КонецЦикла;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, ForNode)
        assert stmt.variable == "Счетчик"
        assert isinstance(stmt.start, LiteralNode)
        assert stmt.start.value == 1
        assert isinstance(stmt.end, LiteralNode)
        assert stmt.end.value == 10
        assert len(stmt.body) == 1

    def test_foreach_loop(self):
        """Test for-each loop."""
        code = """
        Функция Тест()
            Для Каждого Элемент Из Массив Цикл
                Сообщить(Элемент);
            КонецЦикла;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, ForEachNode)
        assert stmt.variable == "Элемент"
        assert isinstance(stmt.collection, IdentifierNode)
        assert stmt.collection.name == "Массив"
        assert len(stmt.body) == 1


class TestTryCatch:
    """Test try-catch parsing."""

    def test_try_catch(self):
        """Test try-catch statement."""
        code = """
        Функция Тест()
            Попытка
                А = 1;
            Исключение
                Б = 2;
            КонецПопытки;
        КонецФункции
        """
        ast = parse(code)
        stmt = ast.functions[0].body[0]
        assert isinstance(stmt, TryNode)
        assert len(stmt.try_body) == 1
        assert len(stmt.except_body) == 1


class TestExpressions:
    """Test expression parsing."""

    def test_literal_number(self):
        """Test number literal."""
        code = "Функция Тест() Возврат 42; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, LiteralNode)
        assert expr.value == 42
        assert expr.literal_type == "number"

    def test_literal_string(self):
        """Test string literal."""
        code = 'Функция Тест() Возврат "Привет"; КонецФункции'
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, LiteralNode)
        assert expr.value == "Привет"
        assert expr.literal_type == "string"

    def test_literal_boolean_true(self):
        """Test boolean true literal."""
        code = "Функция Тест() Возврат Истина; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, LiteralNode)
        assert expr.value is True

    def test_literal_boolean_false(self):
        """Test boolean false literal."""
        code = "Функция Тест() Возврат Ложь; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, LiteralNode)
        assert expr.value is False

    def test_literal_undefined(self):
        """Test undefined literal."""
        code = "Функция Тест() Возврат Неопределено; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, LiteralNode)
        assert expr.value is None

    def test_identifier(self):
        """Test identifier."""
        code = "Функция Тест() Возврат МояПеременная; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, IdentifierNode)
        assert expr.name == "МояПеременная"

    def test_binary_op_addition(self):
        """Test addition binary operation."""
        code = "Функция Тест() Возврат А + Б; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, BinaryOpNode)
        assert expr.operator == "+"
        assert isinstance(expr.left, IdentifierNode)
        assert isinstance(expr.right, IdentifierNode)

    def test_binary_op_precedence(self):
        """Test operator precedence."""
        code = "Функция Тест() Возврат А + Б * В; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, BinaryOpNode)
        assert expr.operator == "+"
        # Right side should be Б * В
        assert isinstance(expr.right, BinaryOpNode)
        assert expr.right.operator == "*"

    def test_unary_minus(self):
        """Test unary minus."""
        code = "Функция Тест() Возврат -А; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, UnaryOpNode)
        assert expr.operator == "-"
        assert isinstance(expr.operand, IdentifierNode)

    def test_unary_not(self):
        """Test unary NOT."""
        code = "Функция Тест() Возврат НЕ А; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, UnaryOpNode)
        assert expr.operator == "НЕ"

    def test_function_call_no_args(self):
        """Test function call without arguments."""
        code = "Функция Тест() Возврат МояФункция(); КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, CallNode)
        assert isinstance(expr.function, IdentifierNode)
        assert expr.function.name == "МояФункция"
        assert len(expr.arguments) == 0

    def test_function_call_with_args(self):
        """Test function call with arguments."""
        code = "Функция Тест() Возврат МояФункция(А, Б, В); КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, CallNode)
        assert len(expr.arguments) == 3

    def test_member_access(self):
        """Test member access."""
        code = "Функция Тест() Возврат Объект.Свойство; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, MemberAccessNode)
        assert isinstance(expr.object, IdentifierNode)
        assert expr.object.name == "Объект"
        assert expr.member == "Свойство"

    def test_method_call(self):
        """Test method call."""
        code = "Функция Тест() Возврат Объект.Метод(А); КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, CallNode)
        assert isinstance(expr.function, MemberAccessNode)
        assert expr.function.member == "Метод"

    def test_new_expression(self):
        """Test new expression."""
        code = "Функция Тест() Возврат Новый Массив; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, NewNode)
        assert expr.type_name == "Массив"

    def test_new_expression_with_args(self):
        """Test new expression with arguments."""
        code = "Функция Тест() Возврат Новый Массив(10, 20); КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, NewNode)
        assert len(expr.arguments) == 2

    def test_parenthesized_expression(self):
        """Test parenthesized expression."""
        code = "Функция Тест() Возврат (А + Б) * В; КонецФункции"
        ast = parse(code)
        expr = ast.functions[0].body[0].value
        assert isinstance(expr, BinaryOpNode)
        assert expr.operator == "*"
        # Left side should be (А + Б)
        assert isinstance(expr.left, BinaryOpNode)
        assert expr.left.operator == "+"


class TestComplexScenarios:
    """Test complex parsing scenarios."""

    def test_complete_module(self):
        """Test parsing a complete module."""
        code = """
        Перем ГлобальнаяПеременная;

        &НаСервере
        Функция ПолучитьДанные(Параметр) Экспорт
            Перем Результат;
            Результат = Параметр * 2;
            Возврат Результат;
        КонецФункции

        &НаКлиенте
        Процедура ОбработатьДанные()
            Перем Данные;
            Данные = ПолучитьДанные(10);
            Сообщить(Данные);
        КонецПроцедуры
        """
        ast = parse(code)
        assert len(ast.var_declarations) == 1
        assert len(ast.functions) == 1
        assert len(ast.procedures) == 1
        assert ast.functions[0].is_export
        assert ast.functions[0].annotation == "&НаСервере"
        assert ast.procedures[0].annotation == "&НаКлиенте"

    def test_nested_control_flow(self):
        """Test nested control flow."""
        code = """
        Функция Тест()
            Для Каждого Элемент Из Массив Цикл
                Если Элемент > 0 Тогда
                    Попытка
                        Обработать(Элемент);
                    Исключение
                        Продолжить;
                    КонецПопытки;
                КонецЕсли;
            КонецЦикла;
        КонецФункции
        """
        ast = parse(code)
        func = ast.functions[0]
        # Outer loop
        assert isinstance(func.body[0], ForEachNode)
        # If inside loop
        assert isinstance(func.body[0].body[0], IfNode)
        # Try inside if
        assert isinstance(func.body[0].body[0].then_body[0], TryNode)


class TestErrorHandling:
    """Test parser error handling."""

    def test_missing_semicolon(self):
        """Test error on missing semicolon."""
        code = """
        Функция Тест()
            Перем А
            Возврат А;
        КонецФункции
        """
        with pytest.raises(ParserError) as exc_info:
            parse(code)
        assert "semicolon" in str(exc_info.value).lower() or ";" in str(exc_info.value)

    def test_missing_end_function(self):
        """Test error on missing end function."""
        code = """
        Функция Тест()
            Возврат 1;
        """
        with pytest.raises(ParserError):
            parse(code)

    def test_unexpected_token(self):
        """Test error on unexpected token."""
        code = """
        Функция Тест()
            Возврат +;
        КонецФункции
        """
        with pytest.raises(ParserError):
            parse(code)
