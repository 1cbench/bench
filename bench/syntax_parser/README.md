# 1C Syntax Parser

A comprehensive syntax parser and type inference engine for 1C:Enterprise language (.bsl files).

## Overview

This project provides tools for parsing 1C (1C:Enterprise) modules written in the BSL (Business Script Language), generating Abstract Syntax Trees (AST), and performing type inference to detect syntax and type errors.

## Features

- **Lexical Analysis**: Tokenizes 1C source code, supporting Cyrillic keywords and identifiers
- **Syntax Parsing**: Builds comprehensive AST from token stream
- **Type Inference**: Infers types and detects type errors in 1C code
- **Error Reporting**: Clear, actionable error messages with line/column information
- **No External Dependencies**: Built from scratch for learning and flexibility

## Project Status

🚧 **Under Development** - Currently implementing Step 1: Project Setup

### Implementation Progress

- [x] Step 1: Project Setup
  - [x] Directory structure
  - [x] Base classes (Token, ASTNode, Type, Error)
  - [x] Testing framework setup
- [ ] Step 2: Lexer Implementation
- [ ] Step 3: Parser Implementation
- [ ] Step 4: Symbol Table and Scoping
- [ ] Step 5: Type System
- [ ] Step 6: Type Inference Engine
- [ ] Step 7: Error Detection
- [ ] Step 8: Public API
- [ ] Step 9-10: Testing and Documentation

## Installation

### Development Setup

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd C:\Work\projects\sberdevices\dev\1cbench\bench\bench\syntax_parser
   ```

2. **Activate the virtual environment**:
   ```bash
   c:\Work\projects\sberdevices\dev\1cbench\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package in development mode**:
   ```bash
   pip install -e .
   ```

## Usage

> **Note**: The parser is still under development. The API shown below is the planned interface.

### Basic Usage

```python
from syntax_parser.api import OneCParser

# Create parser instance
parser = OneCParser()

# Read 1C module
with open('Module.bsl', 'r', encoding='utf-8') as f:
    code = f.read()

# Parse to AST
ast = parser.parse(code)
print(f"Parsed {len(ast.functions)} functions and {len(ast.procedures)} procedures")

# Check for errors
errors = parser.check_types(code)
if errors:
    print(f"Found {len(errors)} errors:")
    for error in errors:
        print(f"  {error}")
else:
    print("No errors found!")
```

## Project Structure

```
syntax_parser/
├── syntax_parser/          # Main package
│   ├── lexer/             # Lexical analyzer (tokenizer)
│   │   ├── token.py       # Token definitions
│   │   └── lexer.py       # Lexer implementation
│   ├── parser/            # Syntax parser
│   │   ├── ast_nodes.py   # AST node classes
│   │   └── parser.py      # Parser implementation
│   ├── type_system/       # Type inference
│   │   ├── types.py       # Type classes
│   │   ├── builtins.py    # Built-in functions/types
│   │   └── inference.py   # Type inference engine
│   ├── symbols/           # Symbol table
│   │   └── symbol_table.py
│   ├── errors/            # Error reporting
│   │   └── reporter.py
│   └── api.py             # Public API
├── tests/                 # Test suite
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── fixtures/          # Test .bsl files
├── examples/              # Usage examples
├── requirements.txt       # Dependencies
└── setup.py              # Package setup
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=syntax_parser --cov-report=html

# Run specific test file
pytest tests/test_lexer.py
```

### Code Formatting

```bash
# Format code with black
black syntax_parser/ tests/

# Type check with mypy
mypy syntax_parser/
```

## 1C Language Support

This parser supports the following 1C language features:

### Supported Syntax

- ✅ Variable declarations (`Перем`)
- ✅ Functions and procedures (`Функция`, `Процедура`)
- ✅ Control flow (`Если`, `Пока`, `Для`)
- ✅ Try-catch blocks (`Попытка`, `Исключение`)
- ✅ Object creation (`Новый`)
- ✅ Annotations (`&НаСервере`, `&НаКлиенте`)
- ✅ Async/await (`Асинх`, `Ждать`)

### Type System

- Primitive types: `Число`, `Строка`, `Дата`, `Булево`, `Неопределено`
- Complex types: `Массив`, `Структура`, `Соответствие`
- Object types: `Запрос`, built-in 1C objects
- Function types with parameter and return type inference

## Contributing

This is an educational/internal project. For details on the implementation plan, see [syntax_parser_plan.md](syntax_parser_plan.md).

## License

Internal use only.

## References

- [Implementation Plan](syntax_parser_plan.md) - Detailed 10-week implementation roadmap
- 1C:Enterprise Documentation
- Test fixtures in `c:\Work\projects\sberdevices\dev\1cbench\cfg\`
