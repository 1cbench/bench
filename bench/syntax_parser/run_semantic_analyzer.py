#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for the 1C semantic analyzer.

Usage:
    python run_semantic_analyzer.py <input_file>
    python run_semantic_analyzer.py --help

Examples:
    python run_semantic_analyzer.py examples/sample.txt
    python run_semantic_analyzer.py examples/test_undefined.txt
    python run_semantic_analyzer.py examples/sample.txt --no-builtins
"""

import sys
import argparse
from pathlib import Path
import io

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add the syntax_parser directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from syntax.lexer.lexer import Lexer
from syntax.parser.parser import Parser
from semantic.semantic_analyzer import SemanticAnalyzer
from semantic.builtins.registry import BuiltinRegistry


def analyze_file(file_path: str, verbose: bool = False, use_builtins: bool = True):
    """
    Analyze a 1C source file for semantic errors.

    Args:
        file_path: Path to the 1C source file
        verbose: If True, print additional information
        use_builtins: If True, load 1C built-in functions and types
    """
    # Read the source code
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return 1
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1

    if verbose:
        print(f"Analyzing file: {file_path}")
        print(f"Code length: {len(code)} characters")
        print("-" * 80)

    # Tokenize
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        if verbose:
            print(f"Tokenization complete: {len(tokens)} tokens")

    except Exception as e:
        print(f"Lexer error: {e}")
        return 1

    # Parse
    try:
        parser = Parser(tokens)
        ast = parser.parse()

        if verbose:
            print("Parsing complete")
            print("-" * 80)

    except Exception as e:
        print(f"Parser error: {e}")
        return 1

    # Load builtins if requested
    builtins = None
    if use_builtins:
        builtins = BuiltinRegistry()
        cache_path = Path(__file__).parent / 'builtins_cache.json'
        if cache_path.exists():
            builtins.load_from_cache(cache_path)
            if verbose:
                print(f"Loaded {builtins.function_count} built-in functions and {builtins.type_count} built-in types")
        else:
            if verbose:
                print(f"Warning: builtins_cache.json not found at {cache_path}")
            builtins = None

    # Semantic analysis
    try:
        analyzer = SemanticAnalyzer(builtins=builtins)
        errors = analyzer.analyze(ast)

        if verbose:
            print("Semantic analysis complete")
            if builtins:
                print(f"Symbol table contains {analyzer.symbol_table.get_builtins_count()} built-in symbols")
            print("-" * 80)

    except Exception as e:
        print(f"Semantic analyzer error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Display results
    if errors:
        print(f"\nFound {len(errors)} semantic error(s):\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        return 1
    else:
        print("\n[OK] No semantic errors found!")
        if verbose:
            symbol_table = analyzer.get_symbol_table()
            print(f"\nSymbol table contains {len(symbol_table.scopes[0])} module-level symbols")
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='1C Semantic Analyzer - Detect semantic errors in 1C code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s examples/sample.txt
  %(prog)s examples/test_undefined.txt --verbose
  %(prog)s examples/sample.txt --no-builtins

The analyzer detects:
  - Undefined variable references
  - Undefined function calls
  - Unknown types in 'Новый' expressions
  - And more...

Built-in support:
  By default, 1C platform built-in functions (НСтр, ЗначениеЗаполнено, Сообщить, etc.)
  and types (ТаблицаЗначений, Структура, Массив, etc.) are recognized.
  Use --no-builtins to disable this and report all undefined symbols.
        """
    )

    parser.add_argument(
        '--input_file',
        help='Path to the 1C source file to analyze',
        default="c:/Work/projects/sberdevices/dev/1cbench/bsp_conf/BusinessProcesses/Задание/Ext/ObjectModule.bsl"
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--no-builtins',
        action='store_true',
        help='Disable built-in functions and types recognition'
    )

    args = parser.parse_args()

    # Run analysis
    exit_code = analyze_file(args.input_file, args.verbose, use_builtins=not args.no_builtins)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
