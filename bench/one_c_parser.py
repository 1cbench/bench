import re
from typing import Optional


class OneCParser:
    """Parser for 1C:Enterprise language code."""

    def clean_code(self, code: str) -> str:
        """
        Remove unreadable and invisible Unicode characters from code.

        This includes:
        - Zero Width Space (ZWSP, U+200B)
        - Zero Width Non-Joiner (ZWNJ, U+200C)
        - Zero Width Joiner (ZWJ, U+200D)
        - Left-to-Right Mark (LRM, U+200E)
        - Right-to-Left Mark (RLM, U+200F)
        - Byte Order Mark (BOM, U+FEFF)
        - Other format and control characters

        Args:
            code: String containing 1C code with potential invisible characters

        Returns:
            Cleaned code string
        """
        # List of invisible/unreadable characters to remove
        invisible_chars = [
            '\u200B',  # ZWSP - Zero Width Space
            '\u200C',  # ZWNJ - Zero Width Non-Joiner
            '\u200D',  # ZWJ - Zero Width Joiner
            '\u200E',  # LRM - Left-to-Right Mark
            '\u200F',  # RLM - Right-to-Left Mark
            '\uFEFF',  # BOM - Byte Order Mark (Zero Width No-Break Space)
            '\u202A',  # LRE - Left-to-Right Embedding
            '\u202B',  # RLE - Right-to-Left Embedding
            '\u202C',  # PDF - Pop Directional Formatting
            '\u202D',  # LRO - Left-to-Right Override
            '\u202E',  # RLO - Right-to-Left Override
        ]

        cleaned = code
        for char in invisible_chars:
            cleaned = cleaned.replace(char, '')

        return cleaned

    def extract_func_name(self, code_block: str) -> Optional[str]:
        """
        Extract function or procedure name from 1C language code block.

        Args:
            code_block: String containing 1C code with function/procedure declaration

        Returns:
            Function/procedure name if found, None otherwise

        """
        # Pattern to match:
        # - Функция (Function) or Процедура (Procedure)
        # - followed by whitespace
        # - followed by the name (word characters including Cyrillic)
        # - followed by opening parenthesis
        pattern = r'(?:Функция|Процедура)\s+([А-Яа-яA-Za-z0-9_]+)\s*\('

        match = re.search(pattern, code_block)
        if match:
            return match.group(1)

        return None

    def extract_function_body(self, code_block: str, func_name: str) -> Optional[str]:
        """
        Extract complete function/procedure body from 1C code.

        Args:
            code_block: String containing 1C code
            func_name: Name of the function/procedure to extract

        Returns:
            Complete function/procedure text from declaration to end keyword, or None if not found
        """
        # Pattern to match the function/procedure declaration with the specific name
        # Using DOTALL flag to match across multiple lines
        pattern = rf'((?:Функция|Процедура)\s+{re.escape(func_name)}\s*\([^)]*\)(?:\s+Экспорт)?.*?(?:КонецФункции|КонецПроцедуры))'

        match = re.search(pattern, code_block, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def patch_function(self, module_text: str, func_name: str, patch: str) -> str:
        """
        Replace a function in module_text with the implementation from patch.

        Args:
            module_text: Original module text containing the function to replace
            func_name: Name of the function to replace
            patch: Text containing the new function implementation

        Returns:
            Module text with the function replaced

        Raises:
            ValueError: If function not found in module_text or patch
        """
        # Extract the new function implementation from patch
        new_func_body = self.extract_function_body(patch, func_name)
        if new_func_body is None:
            raise ValueError(f"Function '{func_name}' not found in patch")

        # Extract the old function from module_text
        old_func_body = self.extract_function_body(module_text, func_name)
        if old_func_body is None:
            raise ValueError(f"Function '{func_name}' not found in module_text")

        # Replace the old function with the new one
        patched_module = module_text.replace(old_func_body, new_func_body)

        return patched_module


if __name__ == '__main__':
    # Test the parser
    test_code = """Функция ЗаполнитьТабличнуюЧастьОстатками(ДокументОбъект) Экспорт

    // Очищаем табличную часть перед заполнением
    ДокументОбъект.Товары.Очистить();

КонецФункции"""

    parser = OneCParser()
    func_name = parser.extract_func_name(test_code)

    expected = "ЗаполнитьТабличнуюЧастьОстатками"

    if func_name == expected:
        print("Test passed! Function name extracted successfully.")
        print(f"Function name length: {len(func_name)} characters")
    else:
        print(f"Test FAILED!")
        print(f"Expected length: {len(expected)}, got: {len(func_name)}")
        print(f"Match: {func_name == expected}")
        raise AssertionError(f"Function name mismatch")
