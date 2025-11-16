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


def analyze_file(file_path: str, verbose: bool = False):
    """
    Analyze a 1C source file for semantic errors.

    Args:
        file_path: Path to the 1C source file
        verbose: If True, print additional information
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

    # Semantic analysis
    try:
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(ast)

        if verbose:
            print("Semantic analysis complete")
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

The analyzer detects:
  - Undefined variable references
  - Undefined function calls
  - Assignment to undefined variables
  - And more...
        """
    )

    parser.add_argument(
        'input_file',
        help='Path to the 1C source file to analyze'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Run analysis
    exit_code = analyze_file(args.input_file, args.verbose)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
