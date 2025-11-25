#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test case-insensitive keyword handling."""

import sys
import io

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from syntax_parser.lexer import Lexer
from syntax_parser.parser import Parser

# Test various case combinations
code = """
ФУНКЦИЯ Тест()
    ПЕРЕМ переменная;
    еСлИ переменная > 0 тОгДа
        ВоЗвРаТ переменная;
    иначЕ
        возврат 0;
    КоНеЦеСлИ;
кОнЕцфУнКцИи
"""

print("Testing case-insensitive keywords...")
print("=" * 80)
print("Code:")
print(code)
print("=" * 80)

try:
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print('\n✓ Successfully parsed code with mixed-case keywords!')
    print(f'  Functions: {len(ast.functions)}')
    print(f'  Procedures: {len(ast.procedures)}')

    # Test more variations
    test_cases = [
        ("перем", "lowercase Перем"),
        ("ПЕРЕМ", "uppercase ПЕРЕМ"),
        ("ПеРеМ", "mixed PeReM"),
        ("если", "lowercase если"),
        ("ЕСЛИ", "uppercase ЕСЛИ"),
        ("конецфункции", "lowercase конецфункции"),
        ("КОНЕЦФУНКЦИИ", "uppercase КОНЕЦФУНКЦИИ"),
        ("КоНеЦфУнКцИи", "mixed КоНеЦфУнКцИи"),
    ]

    print("\n" + "=" * 80)
    print("Testing individual keywords:")
    print("=" * 80)
    for keyword, description in test_cases:
        lexer = Lexer(keyword)
        tokens = lexer.tokenize()
        if tokens and not tokens[0].type.name == "IDENTIFIER":
            print(f"✓ {description:30} -> {tokens[0].type.name}")
        else:
            print(f"✗ {description:30} -> NOT RECOGNIZED")

except Exception as e:
    print(f'\n✗ Error: {e}')
    import traceback
    traceback.print_exc()
