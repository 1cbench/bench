#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parser demonstration script.

This script demonstrates the 1C parser's ability to build ASTs from 1C code.
"""

import sys
import io

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from bench.syntax_parser.syntax.lexer import Lexer, LexerError
from bench.syntax_parser.syntax.parser import Parser, ParserError, ASTPrettyPrinter


def print_separator(title: str = ""):
    """Print a visual separator with optional title."""
    if title:
        print(f"\n{'=' * 80}")
        print(f" {title}")
        print('=' * 80)
    else:
        print('-' * 80)


def parse_and_print(code: str, description: str = ""):
    """Parse code and print the AST."""
    if description:
        print_separator(description)

    print("\nSource code:")
    print_separator()
    print(code)

    try:
        # Tokenize
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        # Parse
        parser = Parser(tokens)
        ast = parser.parse()

        # Pretty print AST
        printer = ASTPrettyPrinter()
        ast_str = printer.print_ast(ast)

        print("\nAST:")
        print_separator()
        print(ast_str)

        # Statistics
        print("\nStatistics:")
        print_separator()
        print(f"Variable declarations: {len(ast.var_declarations)}")
        print(f"Functions: {len(ast.functions)}")
        print(f"Procedures: {len(ast.procedures)}")

        return True

    except (LexerError, ParserError) as e:
        print(f"\n✗ {type(e).__name__}: {e}")
        return False


def demo_variable_declarations():
    """Demo: Variable declarations."""
    code = """
    Перем ГлобальнаяПеременная;
    Перем Счетчик, Результат, Флаг;
    """
    parse_and_print(code, "Demo 1: Variable Declarations")


def demo_simple_function():
    """Demo: Simple function."""
    code = """
    Функция СложитьЧисла(А, Б)
    перем Сумма;
        Если А > Б Тогда
            Возврат А + Б;
        Иначе
            Возврат Б - КакаяТоНеобъявленнаяПеременная;
        КонецЕсли;
    КонецФункции
    """
    parse_and_print(code, "Demo 2: Simple Function")


def demo_function_with_export():
    """Demo: Function with export."""
    code = """
    Функция ПолучитьЗначение(Параметр) Экспорт
        Перем Результат;
        Результат = Параметр * 2;
        Возврат Результат;
    КонецФункции
    """
    parse_and_print(code, "Demo 3: Exported Function")


def demo_procedure():
    """Demo: Procedure."""
    code = """
    Процедура ВывестиСообщение(Текст)
        Сообщить(Текст);
    КонецПроцедуры
    """
    parse_and_print(code, "Demo 4: Procedure")


def demo_if_statement():
    """Demo: If statement."""
    code = """
    Функция ПроверитьЗначение(Значение)
        Если Значение > 100 Тогда
            Возврат "Большое";
        ИначеЕсли Значение > 50 Тогда
            Возврат "Среднее";
        Иначе
            Возврат "Маленькое";
        КонецЕсли;
    КонецФункции
    """
    parse_and_print(code, "Demo 5: If Statement with ElseIf and Else")


def demo_while_loop():
    """Demo: While loop."""
    code = """
    Функция ПоискЭлемента(Массив, Значение)
        Перем Индекс;
        Индекс = 0;

        Пока Индекс < Массив.Количество() Цикл
            Если Массив[Индекс] = Значение Тогда
                Возврат Индекс;
            КонецЕсли;
            Индекс = Индекс + 1;
        КонецЦикла;

        Возврат -1;
    КонецФункции
    """
    parse_and_print(code, "Demo 6: While Loop")


def demo_for_loop():
    """Demo: For loop."""
    code = """
    Функция СуммаЧисел(Начало, Конец)
        Перем Сумма, Число;
        Сумма = 0;

        Для Число = Начало По Конец Цикл
            Сумма = Сумма + Число;
        КонецЦикла;

        Возврат Сумма;
    КонецФункции
    """
    parse_and_print(code, "Demo 7: Numeric For Loop")


def demo_foreach_loop():
    """Demo: For-each loop."""
    code = """
    Функция НайтиМаксимум(Массив)
        Перем Максимум, Элемент;
        Максимум = Неопределено;

        Для Каждого Элемент Из Массив Цикл
            Если Максимум = Неопределено ИЛИ Элемент > Максимум Тогда
                Максимум = Элемент;
            КонецЕсли;
        КонецЦикла;

        Возврат Максимум;
    КонецФункции
    """
    parse_and_print(code, "Demo 8: For-Each Loop")


def demo_try_catch():
    """Demo: Try-catch."""
    code = """
    Функция БезопасноеПреобразование(Значение)
        Перем Результат;

        Попытка
            Результат = Число(Значение);
        Исключение
            Результат = 0;
        КонецПопытки;

        Возврат Результат;
    КонецФункции
    """
    parse_and_print(code, "Demo 9: Try-Catch")


def demo_complex_expressions():
    """Demo: Complex expressions."""
    code = """
    Функция ВычислитьСкидку(Цена, Процент, ЕстьБонус)
        Перем Скидка, ИтоговаяЦена;

        Скидка = Цена * Процент / 100;

        Если ЕстьБонус И Скидка > 100 Тогда
            Скидка = Скидка * 1.1;
        КонецЕсли;

        ИтоговаяЦена = Цена - Скидка;

        Возврат ИтоговаяЦена;
    КонецФункции
    """
    parse_and_print(code, "Demo 10: Complex Expressions")


def demo_member_access_and_calls():
    """Demo: Member access and method calls."""
    code = """
    Функция ПолучитьДанные()
        Перем Запрос, Результат;

        Запрос = Новый Запрос;
        Запрос.Текст = "ВЫБРАТЬ * ИЗ Справочник.Товары";
        Запрос.УстановитьПараметр("Параметр", Истина);

        Результат = Запрос.Выполнить();

        Возврат Результат.Выбрать();
    КонецФункции
    """
    parse_and_print(code, "Demo 11: Member Access and Method Calls")


def demo_annotations():
    """Demo: Annotations."""
    code = """
    &НаСервере
    Функция ПолучитьДанныеНаСервере(Параметр1, Параметр2) Экспорт
        Возврат Параметр1 + Параметр2;
    КонецФункции

    &НаКлиенте
    Процедура ОбработатьНажатие()
        Перем Результат;
        Результат = ПолучитьДанныеНаСервере(10, 20);
        Сообщить(Результат);
    КонецПроцедуры
    """
    parse_and_print(code, "Demo 12: Annotations")


def demo_async_await():
    """Demo: Async/await."""
    code = """
    &НаКлиенте
    Асинх Процедура ЗагрузитьДанные()
        Перем Данные;
        Данные = Ждать ЗагрузитьДанныеАсинх();
        ОтобразитьДанные(Данные);
    КонецПроцедуры
    """
    parse_and_print(code, "Demo 13: Async/Await")


def demo_complete_module():
    """Demo: Complete module with everything."""
    code = """
    Перем МодульнаяПеременная;

    &НаСервере
    Функция РассчитатьСумму(Массив, Условие) Экспорт
        Перем Сумма, Элемент;

        Сумма = 0;

        Попытка
            Для Каждого Элемент Из Массив Цикл
                Если ТипЗнч(Элемент) = Тип("Число") Тогда
                    Если Условие(Элемент) Тогда
                        Сумма = Сумма + Элемент;
                    КонецЕсли;
                КонецЕсли;
            КонецЦикла;
        Исключение
            Сумма = Неопределено;
        КонецПопытки;

        Возврат Сумма;
    КонецФункции

    &НаКлиенте
    Процедура ПроцедураНаКлиенте(Параметр) Экспорт
        Перем Результат;

        Результат = РассчитатьСумму(Параметр, Ложь);

        Если Результат <> Неопределено Тогда
            Сообщить("Сумма: " + Результат);
        Иначе
            Сообщить("Ошибка расчета");
        КонецЕсли;
    КонецПроцедуры
    """
    parse_and_print(code, "Demo 14: Complete Module")


def demo_error_handling():
    """Demo: Error handling."""
    print_separator("Demo 15: Error Handling")

    # Missing semicolon
    print("\nTest 1: Missing semicolon")
    code1 = """
    Функция Тест()
        Перем А
        Возврат А;
    КонецФункции
    """
    print(f"Code: {code1}")
    parse_and_print(code1, "")

    # Missing end function
    print("\nTest 2: Missing КонецФункции")
    code2 = """
    Функция Тест()
        Возврат 1;
    """
    print(f"Code: {code2}")
    parse_and_print(code2, "")

    # Invalid expression
    print("\nTest 3: Invalid expression")
    code3 = """
    Функция Тест()
        Возврат +;
    КонецФункции
    """
    print(f"Code: {code3}")
    parse_and_print(code3, "")


def interactive_mode():
    """Interactive mode for testing custom code."""
    print_separator("Interactive Mode")
    print("\nEnter 1C code to parse (type 'exit' to quit, 'demos' to run all demos)")
    print("You can enter multiple lines - end with an empty line.\n")

    while True:
        print("\n> ", end='')
        lines = []

        # Read multi-line input
        while True:
            try:
                line = input()
                if not line:
                    break
                if line.strip().lower() == 'exit':
                    print("\nGoodbye!")
                    return
                if line.strip().lower() == 'demos':
                    run_all_demos()
                    print("\n> ", end='')
                    continue
                lines.append(line)
            except EOFError:
                return

        if not lines:
            continue

        code = '\n'.join(lines)
        parse_and_print(code)


def run_all_demos():
    """Run all demonstration functions."""
    demo_variable_declarations()
    demo_simple_function()
    demo_function_with_export()
    demo_procedure()
    demo_if_statement()
    demo_while_loop()
    demo_for_loop()
    demo_foreach_loop()
    demo_try_catch()
    demo_complex_expressions()
    demo_member_access_and_calls()
    demo_annotations()
    demo_async_await()
    demo_complete_module()
    demo_error_handling()


def main():
    """Main entry point."""
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                  1C Language Parser Demonstration                     ║
    ║                                                                       ║
    ║  This script demonstrates the parser's ability to build ASTs from    ║
    ║  1C code, showing support for all language constructs.               ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--interactive' or sys.argv[1] == '-i':
            interactive_mode()
        elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
Usage: python run_parser.py [options]

Options:
  (no options)        Run all demonstration examples
  -i, --interactive   Enter interactive mode to test custom code
  -h, --help          Show this help message

Examples:
  python run_parser.py                  # Run all demos
  python run_parser.py --interactive    # Interactive mode
            """)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        # run_all_demos()
        demo_simple_function()

        print("\n" + "=" * 80)
        print("Demonstrations complete!")
        print("=" * 80)
        print("\nTip: Run with --interactive flag to test your own code:")
        print("  python run_parser.py --interactive")


if __name__ == "__main__":
    main()
