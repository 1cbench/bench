#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lexer demonstration script.

This script demonstrates the 1C lexer's functionality by tokenizing
various 1C code samples and displaying the results.
"""

import sys
import io

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from syntax_parser.lexer import Lexer, LexerError, TokenType


def print_separator(title: str = ""):
    """Print a visual separator with optional title."""
    if title:
        print(f"\n{'=' * 80}")
        print(f" {title}")
        print('=' * 80)
    else:
        print('-' * 80)


def print_tokens(tokens, show_all: bool = False):
    """
    Print tokens in a formatted table.

    Args:
        tokens: List of tokens to print
        show_all: If True, show newlines and comments; otherwise filter them
    """
    print(f"\n{'Type':<30} {'Value':<30} {'Position':<15}")
    print_separator()

    for token in tokens:
        # Skip newlines and comments unless show_all is True
        if not show_all and token.type in (TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF):
            continue

        # Format token type name
        type_name = token.type.name

        # Format value (escape special chars)
        value = token.value.replace('\n', '\\n').replace('\t', '\\t')
        if len(value) > 28:
            value = value[:25] + '...'

        # Format position
        position = f"{token.line}:{token.column}"

        print(f"{type_name:<30} {value:<30} {position:<15}")


def demo_basic_tokens():
    """Demonstrate tokenization of basic elements."""
    print_separator("Demo 1: Basic Tokens")

    code = """
    Перем МояПеременная;
    Перем Счетчик, Результат;
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print_tokens(tokens)
    print(f"\nTotal tokens (excluding whitespace): {len([t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF)])}")


def demo_function_declaration():
    """Demonstrate tokenization of a function declaration."""
    print_separator("Demo 2: Function Declaration")

    code = """
    Функция СложитьЧисла(Число1, Число2) Экспорт
        Перем Результат;
        Результат = Число1 + Число2;
        Возврат Результат;
    КонецФункции
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print_tokens(tokens)


def demo_control_structures():
    """Demonstrate tokenization of control flow structures."""
    print_separator("Demo 3: Control Structures")

    code = """
    Если Условие Тогда
        Сообщить("Истина");
    ИначеЕсли ДругоеУсловие Тогда
        Сообщить("Другое");
    Иначе
        Сообщить("Ложь");
    КонецЕсли;
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print_tokens(tokens)


def demo_operators_and_literals():
    """Demonstrate tokenization of operators and literals."""
    print_separator("Demo 4: Operators and Literals")

    code = """
    Результат = (10 + 20) * 3.14;
    Текст = "Привет, мир!";
    Флаг = Истина;
    Дата = '20240115';
    Условие = (А > Б) И (В <= Г) ИЛИ НЕ (Д <> Е);
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print_tokens(tokens)


def demo_loops():
    """Demonstrate tokenization of loop structures."""
    print_separator("Demo 5: Loops")

    code = """
    Для Счетчик = 1 По 10 Цикл
        Сообщить(Счетчик);
    КонецЦикла;

    Пока Условие Цикл
        ВыполнитьДействие();
    КонецЦикла;

    Для Каждого Элемент Из Коллекция Цикл
        ОбработатьЭлемент(Элемент);
    КонецЦикла;
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print_tokens(tokens)


def demo_annotations_and_comments():
    """Demonstrate tokenization of annotations and comments."""
    print_separator("Demo 6: Annotations and Comments")

    code = """
    // Это функция для работы на сервере
    &НаСервере
    Функция ПолучитьДанные(Параметр1, Параметр2) Экспорт
        // Создаем новый объект
        Запрос = Новый Запрос;
        Возврат Запрос.Выполнить();
    КонецФункции

    &НаКлиенте
    Асинх Процедура ОбработатьНажатие()
        Результат = Ждать ПолучитьДанныеАсинх();
    КонецПроцедуры
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    # Show all tokens including comments
    print("\nAll tokens (including comments and newlines):")
    print_tokens(tokens, show_all=True)


def demo_complex_example():
    """Demonstrate tokenization of a complex, realistic example."""
    print_separator("Demo 7: Complex Example")

    code = """
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
    """

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print_tokens(tokens)

    # Statistics
    token_counts = {}
    for token in tokens:
        if token.type not in (TokenType.NEWLINE, TokenType.EOF):
            type_name = token.type.name
            token_counts[type_name] = token_counts.get(type_name, 0) + 1

    print("\nToken Statistics:")
    print_separator()
    for token_type, count in sorted(token_counts.items(), key=lambda x: -x[1]):
        print(f"{token_type:<30} {count:>5}")


def demo_error_handling():
    """Demonstrate lexer error handling."""
    print_separator("Demo 8: Error Handling")

    # Unterminated string
    print("\nTest 1: Unterminated string")
    code1 = 'Текст = "Незакрытая строка'
    print(f"Code: {code1}")

    try:
        lexer = Lexer(code1)
        tokens = lexer.tokenize()
    except LexerError as e:
        print(f"✓ Error caught: {e}")

    # Unexpected character
    print("\nTest 2: Unexpected character")
    code2 = 'Перем А @ Б;'
    print(f"Code: {code2}")

    try:
        lexer = Lexer(code2)
        tokens = lexer.tokenize()
    except LexerError as e:
        print(f"✓ Error caught: {e}")

    # Valid escaped quotes in string
    print("\nTest 3: Escaped quotes (should succeed)")
    code3 = 'Текст = "Строка с ""кавычками"" внутри";'
    print(f"Code: {code3}")

    try:
        lexer = Lexer(code3)
        tokens = lexer.tokenize()
        print("✓ Tokenization successful!")
        print_tokens(tokens)
    except LexerError as e:
        print(f"✗ Unexpected error: {e}")


def demo_string_literals():
    """Demonstrate string literal handling."""
    print_separator("Demo 9: String Literals")

    code = '''
    ПростаяСтрока = "Привет";
    СтрокаСКавычками = "Он сказал: ""Привет""";
    МногострочнаяСтрока = "Первая строка
Вторая строка
Третья строка";
    ПустаяСтрока = "";
    '''

    print("\nSource code:")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print("\nString tokens:")
    print_separator()
    for token in tokens:
        if token.type == TokenType.LITERAL_STRING:
            # Show the actual value with escaped newlines
            display_value = repr(token.value)
            print(f"String at {token.line}:{token.column}: {display_value}")


def interactive_mode():
    """Interactive mode for testing custom code."""
    print_separator("Interactive Mode")
    print("\nEnter 1C code to tokenize (type 'exit' to quit, 'demos' to run all demos)")
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

        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            print_tokens(tokens)
            print(f"\nTotal tokens: {len([t for t in tokens if t.type != TokenType.EOF])}")
        except LexerError as e:
            print(f"\n✗ {e}")


def run_all_demos():
    """Run all demonstration functions."""
    demo_basic_tokens()
    demo_function_declaration()
    demo_control_structures()
    demo_operators_and_literals()
    demo_loops()
    demo_annotations_and_comments()
    demo_complex_example()
    demo_string_literals()
    demo_error_handling()


def main():
    """Main entry point."""
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                  1C Language Lexer Demonstration                      ║
    ║                                                                       ║
    ║  This script demonstrates the lexer's ability to tokenize 1C code    ║
    ║  including keywords, operators, literals, and special constructs.    ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--interactive' or sys.argv[1] == '-i':
            interactive_mode()
        elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
Usage: python run_lexer.py [options]

Options:
  (no options)        Run all demonstration examples
  -i, --interactive   Enter interactive mode to test custom code
  -h, --help          Show this help message

Examples:
  python run_lexer.py                  # Run all demos
  python run_lexer.py --interactive    # Interactive mode
            """)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        # run_all_demos()

        demo_function_declaration()
        print("\n" + "=" * 80)
        print("Demonstrations complete!")
        print("=" * 80)
        print("\nTip: Run with --interactive flag to test your own code:")
        print("  python run_lexer.py --interactive")


if __name__ == "__main__":
    main()
