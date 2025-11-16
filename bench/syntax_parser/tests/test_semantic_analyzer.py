"""
Comprehensive tests for the semantic analyzer.

Tests cover Phase 1: Undefined variable detection
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from syntax_parser.lexer.lexer import Lexer
from syntax_parser.parser.parser import Parser
from semantic.semantic_analyzer import SemanticAnalyzer
from semantic.errors import SemanticError


class TestSemanticAnalyzer(unittest.TestCase):
    """Test cases for semantic analyzer."""

    def _analyze_code(self, code: str) -> list[SemanticError]:
        """Helper method to analyze code and return errors."""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(ast)
        return errors

    # =========================================================================
    # Test 1: Undefined Variable
    # =========================================================================

    def test_undefined_variable_in_function(self):
        """Test detection of undefined variable in function."""
        code = """
        Функция Тест()
            Возврат х;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, 'undefined_variable')
        self.assertIn('х', errors[0].message)

    def test_undefined_variable_in_assignment(self):
        """Test detection of undefined variable used in assignment value."""
        code = """
        Функция Тест()
            Перем а;
            а = б + 5;
            Возврат а;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, 'undefined_variable')
        self.assertIn('б', errors[0].message)

    def test_assignment_to_undefined_variable(self):
        """Test detection of assignment to undefined variable."""
        code = """
        Функция Тест()
            х = 5;
            Возврат х;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # Should have error for assignment to undefined variable
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('х' in error.message for error in errors))

    # =========================================================================
    # Test 2: Valid Local Variable
    # =========================================================================

    def test_valid_local_variable(self):
        """Test that properly declared local variables don't generate errors."""
        code = """
        Функция Тест()
            Перем х;
            х = 5;
            Возврат х;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_multiple_local_variables(self):
        """Test multiple local variables in one declaration."""
        code = """
        Функция Тест()
            Перем а, б, с;
            а = 1;
            б = 2;
            с = а + б;
            Возврат с;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 3: Parameter Usage
    # =========================================================================

    def test_function_parameters(self):
        """Test that function parameters are recognized as defined."""
        code = """
        Функция Тест(а, б)
            Возврат а + б;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_procedure_parameters(self):
        """Test that procedure parameters are recognized as defined."""
        code = """
        Процедура Вывести(текст, значение)
            Перем результат;
            результат = текст + значение;
        КонецПроцедуры
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_parameters_with_default_values(self):
        """Test parameters with default values."""
        code = """
        Функция Тест(а, б = 10)
            Возврат а + б;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 4: Loop Variables
    # =========================================================================

    def test_for_loop_variable(self):
        """Test that FOR loop variables are recognized."""
        code = """
        Функция Сумма()
            Перем с;
            с = 0;
            Для і = 1 По 10 Цикл
                с = с + і;
            КонецЦикла;
            Возврат с;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_foreach_loop_variable(self):
        """Test that FOR EACH loop variables are recognized."""
        code = """
        Функция ОбработатьМассив(массив)
            Перем сумма;
            сумма = 0;
            Для Каждого элемент Из массив Цикл
                сумма = сумма + элемент;
            КонецЦикла;
            Возврат сумма;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_loop_variable_scope(self):
        """Test that loop variables are function-scoped (1C behavior)."""
        code = """
        Функция Тест()
            Для і = 1 По 5 Цикл
            КонецЦикла;
            Возврат і;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # In 1C, loop variables are function-scoped, so this should be valid
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 5: Module-Level Variables
    # =========================================================================

    def test_module_level_variables(self):
        """Test that module-level variables are accessible in functions."""
        code = """
        Перем МодульнаяПеременная;

        Функция Тест()
            МодульнаяПеременная = 10;
            Возврат МодульнаяПеременная;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_multiple_module_variables(self):
        """Test multiple module-level variables."""
        code = """
        Перем Переменная1, Переменная2, Переменная3;

        Функция Инициализация()
            Переменная1 = 1;
            Переменная2 = 2;
            Переменная3 = 3;
            Возврат Переменная1 + Переменная2 + Переменная3;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 6: Function and Procedure Declarations
    # =========================================================================

    def test_function_call_defined_function(self):
        """Test calling a defined function."""
        code = """
        Функция Помощник()
            Возврат 42;
        КонецФункции

        Функция Главная()
            Перем результат;
            результат = Помощник();
            Возврат результат;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_procedure_call_defined_procedure(self):
        """Test calling a defined procedure."""
        code = """
        Процедура Помощник()
            Перем х;
            х = 1;
        КонецПроцедуры

        Процедура Главная()
            Помощник();
        КонецПроцедуры
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_undefined_function_call(self):
        """Test calling an undefined function."""
        code = """
        Функция Главная()
            Возврат НесуществующаяФункция();
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, 'undefined_variable')
        self.assertIn('НесуществующаяФункция', errors[0].message)

    # =========================================================================
    # Test 7: Variable Scope in Nested Blocks
    # =========================================================================

    def test_variable_in_if_block(self):
        """Test variable declared in IF block (function-scoped in 1C)."""
        code = """
        Функция Тест()
            Если Истина Тогда
                Перем х;
                х = 5;
            КонецЕсли;
            Возврат х;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # In 1C, variables are function-scoped, not block-scoped
        # So this should be valid
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_variable_in_while_loop(self):
        """Test variable declared in WHILE loop."""
        code = """
        Функция Тест()
            Пока Ложь Цикл
                Перем х;
                х = 1;
            КонецЦикла;
            Возврат х;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # In 1C, variables are function-scoped
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_variable_in_try_block(self):
        """Test variable declared in TRY block."""
        code = """
        Функция Тест()
            Попытка
                Перем х;
                х = 10;
            Исключение
                Перем у;
                у = 20;
            КонецПопытки;
            Возврат х + у;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # In 1C, variables are function-scoped
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 8: Complex Expressions
    # =========================================================================

    def test_binary_operations(self):
        """Test variable usage in binary operations."""
        code = """
        Функция Вычислить(а, б)
            Перем результат;
            результат = (а + б) * 2 - а / б;
            Возврат результат;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_undefined_in_binary_operation(self):
        """Test undefined variable in binary operation."""
        code = """
        Функция Тест(а)
            Возврат а + неопределённая;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 1)
        self.assertIn('неопределённая', errors[0].message)

    def test_unary_operations(self):
        """Test variable usage in unary operations."""
        code = """
        Функция Тест(флаг)
            Возврат НЕ флаг;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 9: Member Access (basic check)
    # =========================================================================

    def test_member_access_defined_object(self):
        """Test member access on defined object."""
        code = """
        Функция Тест()
            Перем объект;
            объект = Новый Структура;
            Возврат объект.Свойство;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # Should not have errors for undefined 'объект'
        # (property validation is Phase 2)
        undefined_obj_errors = [e for e in errors if 'объект' in e.message]
        self.assertEqual(len(undefined_obj_errors), 0)

    def test_member_access_undefined_object(self):
        """Test member access on undefined object."""
        code = """
        Функция Тест()
            Возврат несуществующий.Свойство;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # Should have error for undefined 'несуществующий'
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('несуществующий' in e.message for e in errors))

    # =========================================================================
    # Test 10: Case Insensitivity
    # =========================================================================

    def test_case_insensitive_variable_reference(self):
        """Test that variable references are case-insensitive."""
        code = """
        Функция Тест()
            Перем МояПеременная;
            МОЯПЕРЕМЕННАЯ = 5;
            Возврат мояпеременная;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_case_insensitive_parameter(self):
        """Test that parameter references are case-insensitive."""
        code = """
        Функция Тест(ПараметрАБВ)
            Возврат параметрабв;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 11: Multiple Errors
    # =========================================================================

    def test_multiple_undefined_variables(self):
        """Test detection of multiple undefined variables."""
        code = """
        Функция Тест()
            Перем а;
            а = б + с + д;
            Возврат а;
        КонецФункции
        """
        errors = self._analyze_code(code)

        # Should find 3 undefined variables: б, с, д
        self.assertEqual(len(errors), 3)
        undefined_names = {e.message for e in errors}
        self.assertTrue(any('б' in msg for msg in undefined_names))
        self.assertTrue(any('с' in msg for msg in undefined_names))
        self.assertTrue(any('д' in msg for msg in undefined_names))

    # =========================================================================
    # Test 12: Edge Cases
    # =========================================================================

    def test_empty_function(self):
        """Test empty function has no errors."""
        code = """
        Функция Пустая()
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0)

    def test_function_with_only_declarations(self):
        """Test function with only variable declarations."""
        code = """
        Функция Тест()
            Перем а, б, с;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0)

    def test_nested_function_calls(self):
        """Test nested function calls with parameters."""
        code = """
        Функция Внутренняя(х)
            Возврат х * 2;
        КонецФункции

        Функция Внешняя(а, б)
            Возврат Внутренняя(а) + Внутренняя(б);
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    # =========================================================================
    # Test 13: Literals and Constants
    # =========================================================================

    def test_literals_in_expressions(self):
        """Test that literals don't cause undefined variable errors."""
        code = """
        Функция Тест()
            Перем х;
            х = 42;
            Возврат х + 10;
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_string_literals(self):
        """Test string literals."""
        code = """
        Функция ПолучитьТекст()
            Возврат "Привет, мир!";
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0)

    # =========================================================================
    # Test 14: Index Access
    # =========================================================================

    def test_array_index_access(self):
        """Test array index access."""
        code = """
        Функция Тест(массив, индекс)
            Возврат массив[индекс];
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_undefined_in_index_access(self):
        """Test undefined variable in index access."""
        code = """
        Функция Тест(массив)
            Возврат массив[неопределённый_индекс];
        КонецФункции
        """
        errors = self._analyze_code(code)

        self.assertEqual(len(errors), 1)
        self.assertIn('неопределённый_индекс', errors[0].message)


if __name__ == '__main__':
    unittest.main()
