# Semantic Analyzer for 1C Language

This package provides semantic analysis for 1C code, detecting errors that are syntactically valid but logically incorrect.

## Overview

The semantic analyzer operates on the Abstract Syntax Tree (AST) produced by the parser and performs multi-pass analysis to detect various types of semantic errors.

## Current Features (Phase 1)

### Undefined Variable Detection

The analyzer detects:
- ✓ Undefined variable references
- ✓ Undefined function/procedure calls
- ✓ Assignment to undefined variables
- ✓ Variables used in expressions, conditions, and return statements

### Scope Management

The analyzer correctly handles:
- ✓ Module-level variables
- ✓ Function/procedure parameters
- ✓ Local variables
- ✓ Loop variables (Для, Для Каждого)
- ✓ Function-scoped variables (1C behavior - variables declared in blocks are visible throughout the function)
- ✓ Case-insensitive identifiers (1C behavior)

## Usage

### Basic Usage

```python
from syntax_parser.lexer.lexer import Lexer
from syntax_parser.parser.parser import Parser
from semantic.semantic_analyzer import SemanticAnalyzer

# Your 1C code
code = """
Функция Тест()
    Перем х;
    х = 5;
    Возврат х + неопределённая;  // Error: 'неопределённая' is undefined
КонецФункции
"""

# Tokenize
lexer = Lexer(code)
tokens = lexer.tokenize()

# Parse
parser = Parser(tokens)
ast = parser.parse()

# Analyze
analyzer = SemanticAnalyzer()
errors = analyzer.analyze(ast)

# Display errors
if errors:
    print(f"Found {len(errors)} error(s):")
    for error in errors:
        print(f"  {error}")
else:
    print("No semantic errors found!")
```

### Command Line Usage

```bash
python run_semantic_analyzer.py examples/sample_code.txt
```

## Architecture

### Components

1. **SemanticAnalyzer** (`semantic_analyzer.py`)
   - Main coordinator class
   - Orchestrates multiple analysis passes
   - Collects and reports all errors

2. **SymbolTable** (`symbol_table.py`)
   - Manages variable scopes using a stack-based approach
   - Supports nested scopes (module → function → blocks)
   - Handles case-insensitive lookups

3. **Symbol** (`symbol_table.py`)
   - Represents a declared symbol (variable, parameter, function, etc.)
   - Tracks declaration location and scope level

4. **SemanticError** (`errors.py`)
   - Represents a semantic error with location and type information

5. **Checkers** (`checkers/`)
   - **VariableCollector**: Builds symbol table by collecting all declarations
   - **UndefinedVariableChecker**: Validates all variable references

### Analysis Passes

The analyzer performs analysis in two passes:

1. **Collection Pass** (VariableCollector)
   - Traverses the AST to collect all variable declarations
   - Builds the symbol table with proper scope handling
   - Collects:
     - Module-level variables
     - Function/procedure declarations
     - Parameters
     - Local variables
     - Loop variables

2. **Validation Pass** (UndefinedVariableChecker)
   - Traverses the AST to check all variable references
   - Reports undefined variables
   - Maintains scope context during traversal

## 1C Language Specifics

The analyzer implements 1C-specific scoping rules:

1. **Function-Scoped Variables**: Variables declared anywhere in a function (even inside IF blocks, loops, etc.) are visible throughout the entire function, not just in the block where they're declared.

2. **Case Insensitivity**: Variable names are case-insensitive (e.g., `МояПеременная`, `МОЯПЕРЕМЕННАЯ`, and `мояпеременная` all refer to the same variable).

3. **Loop Variables**: Loop variables in `Для` and `Для Каждого` loops are automatically declared and scoped to the function.

## Error Types

Currently supported error types:

- `undefined_variable`: Variable referenced but not declared
- `invalid_ast`: Invalid AST structure (shouldn't happen with valid parser output)

## Future Phases

### Phase 2: Property Access Validation
- Type tracking and inference
- Property existence validation
- Type registry for known types

### Phase 3: Additional Checks
- Return path analysis
- Dead code detection
- Type compatibility checking
- Constant folding

## Testing

Run the test suite:

```bash
pytest tests/test_semantic_analyzer.py -v
```

The test suite includes 34 comprehensive tests covering:
- Undefined variable detection
- Valid variable usage
- Parameter handling
- Loop variables
- Module-level variables
- Function/procedure declarations
- Scope management
- Case insensitivity
- Complex expressions
- Edge cases

## Example Errors

```python
# Error: Undefined variable
Функция Тест()
    Возврат х;  // Error: 'х' is not defined
КонецФункции

# Error: Assignment to undefined variable
Функция Тест()
    х = 5;  // Error: Assignment to undefined variable 'х'
    Возврат х;
КонецФункции

# Error: Undefined function call
Функция Главная()
    Возврат НесуществующаяФункция();  // Error: Call to undefined function
КонецФункции
```

## Performance

The analyzer uses the visitor pattern for efficient AST traversal. It makes two complete passes over the AST:
1. Collection pass (O(n))
2. Validation pass (O(n))

Total complexity: O(n) where n is the number of AST nodes.

## Contributing

When adding new semantic checks:

1. Create a new visitor class in `checkers/`
2. Add the visitor to `__init__.py` in the checkers package
3. Integrate it into `SemanticAnalyzer.analyze()`
4. Add comprehensive tests to `test_semantic_analyzer.py`

## License

Part of the 1CBench project.
