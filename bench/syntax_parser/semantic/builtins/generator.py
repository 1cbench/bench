# -*- coding: utf-8 -*-
"""
Generator script to extract 1C built-in functions and types from FileStorage documentation.

This script parses the HTML documentation files in the extracted_docs/FileStorage directory
and creates a JSON cache file (builtins_cache.json) with all function and type names.

Usage:
    python generator.py [--docs-path PATH] [--output PATH] [--verbose]

Example:
    python generator.py --docs-path "c:/Work/projects/sberdevices/dev/1cbench/extracted_docs/FileStorage"
"""

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# Fix Windows console encoding for Cyrillic output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


@dataclass
class ExtractedSymbol:
    """Extracted function or type information."""
    name_ru: str
    name_en: str
    category: str
    source_file: str


class TitleExtractor(HTMLParser):
    """
    HTML parser to extract the title from 1C documentation HTML files.

    Looks for content in <h1 class="V8SH_pagetitle"> tags which contain
    the format: "РусскоеИмя (EnglishName)"
    """

    def __init__(self):
        super().__init__()
        self._in_title = False
        self._title_text = ""
        self._found = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        if tag == 'h1':
            attrs_dict = dict(attrs)
            if attrs_dict.get('class') == 'V8SH_pagetitle':
                self._in_title = True

    def handle_endtag(self, tag: str):
        if tag == 'h1' and self._in_title:
            self._in_title = False
            self._found = True

    def handle_data(self, data: str):
        if self._in_title:
            self._title_text += data

    @property
    def title(self) -> str:
        return self._title_text.strip()


def parse_title(title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse title in format "Глобальный контекст.НСтр (Global context.NStr)"
    or "ТаблицаЗначений (ValueTable)" to extract Russian and English names.

    Returns:
        Tuple of (russian_name, english_name) or (None, None) if parsing failed
    """
    if not title:
        return None, None

    # Pattern: "Something.Name (Something.Name)" or "Name (Name)"
    # We want just the final name part
    match = re.match(r'^(?:.*\.)?(\S+)\s*\((?:.*\.)?(\S+)\)$', title)
    if match:
        return match.group(1), match.group(2)

    # Try simpler pattern without dot prefix
    match = re.match(r'^(\S+)\s*\((\S+)\)$', title)
    if match:
        return match.group(1), match.group(2)

    return None, None


def extract_from_html(html_path: Path) -> Optional[Tuple[str, str]]:
    """
    Extract Russian and English names from an HTML documentation file.

    Args:
        html_path: Path to the HTML file

    Returns:
        Tuple of (russian_name, english_name) or None if extraction failed
    """
    try:
        # Try different encodings
        content = None
        for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'utf-16']:
            try:
                content = html_path.read_text(encoding=encoding)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            return None

        parser = TitleExtractor()
        parser.feed(content)

        if parser.title:
            return parse_title(parser.title)

    except Exception as e:
        # Silently ignore parsing errors
        pass

    return None


def scan_global_functions(methods_path: Path, verbose: bool = False) -> List[ExtractedSymbol]:
    """
    Scan Global context/methods directory for built-in functions.

    Args:
        methods_path: Path to "Global context/methods" directory
        verbose: Print progress information

    Returns:
        List of extracted function symbols
    """
    functions = []

    if not methods_path.exists():
        if verbose:
            print(f"Warning: Methods path not found: {methods_path}")
        return functions

    # Iterate through catalog subdirectories
    for catalog_dir in methods_path.iterdir():
        if not catalog_dir.is_dir():
            continue
        if catalog_dir.name.startswith('__'):
            continue

        category = catalog_dir.name

        # Find HTML files in this catalog
        for html_file in catalog_dir.glob('*.html'):
            result = extract_from_html(html_file)
            if result:
                name_ru, name_en = result
                if name_ru and name_en:
                    functions.append(ExtractedSymbol(
                        name_ru=name_ru,
                        name_en=name_en,
                        category=category,
                        source_file=str(html_file.relative_to(methods_path.parent.parent))
                    ))
                    if verbose:
                        print(f"  Function: {name_ru} ({name_en})")

    return functions


def scan_types(objects_path: Path, verbose: bool = False) -> List[ExtractedSymbol]:
    """
    Scan objects directory for built-in types.

    Types are found in catalog*/catalog*/ directories where there's a TypeName.html file
    with the same name as the directory.

    Args:
        objects_path: Path to "objects" directory
        verbose: Print progress information

    Returns:
        List of extracted type symbols
    """
    types = []
    seen_types: Set[str] = set()

    if not objects_path.exists():
        if verbose:
            print(f"Warning: Objects path not found: {objects_path}")
        return types

    def scan_catalog(catalog_path: Path, category: str = ""):
        """Recursively scan catalog directories for types."""
        if not catalog_path.is_dir():
            return

        for item in catalog_path.iterdir():
            if item.is_dir() and item.name.startswith('catalog'):
                # Check if there's an HTML file with type definition
                scan_catalog(item, item.name)

            elif item.is_dir() and not item.name.startswith('__'):
                # This might be a type directory (e.g., "ValueTable")
                type_html = item / f"{item.name}.html"
                if not type_html.exists():
                    # Try finding any HTML file in this directory that defines the type
                    for html_file in item.glob('*.html'):
                        result = extract_from_html(html_file)
                        if result:
                            name_ru, name_en = result
                            if name_ru and name_en:
                                key = name_ru.lower()
                                if key not in seen_types:
                                    seen_types.add(key)
                                    types.append(ExtractedSymbol(
                                        name_ru=name_ru,
                                        name_en=name_en,
                                        category=category,
                                        source_file=str(html_file.relative_to(objects_path))
                                    ))
                                    if verbose:
                                        print(f"  Type: {name_ru} ({name_en})")
                        break

            elif item.suffix == '.html' and not item.name.startswith('__'):
                # Check HTML files directly in catalog directories
                result = extract_from_html(item)
                if result:
                    name_ru, name_en = result

                    # Skip if this looks like a method/property (contains dot in title)
                    # Types usually have simple names without dots
                    if name_ru and name_en and '.' not in name_ru:
                        key = name_ru.lower()
                        if key not in seen_types:
                            seen_types.add(key)
                            types.append(ExtractedSymbol(
                                name_ru=name_ru,
                                name_en=name_en,
                                category=category,
                                source_file=str(item.relative_to(objects_path))
                            ))
                            if verbose:
                                print(f"  Type: {name_ru} ({name_en})")

    # Scan all top-level catalog directories
    for item in objects_path.iterdir():
        if item.is_dir() and item.name.startswith('catalog'):
            if verbose:
                print(f"Scanning catalog: {item.name}")
            scan_catalog(item, item.name)

    return types


def generate_cache(docs_path: Path, output_path: Path, verbose: bool = False) -> bool:
    """
    Generate the builtins_cache.json file from FileStorage documentation.

    Args:
        docs_path: Path to FileStorage directory
        output_path: Path to output JSON file
        verbose: Print progress information

    Returns:
        True if generation succeeded, False otherwise
    """
    objects_path = docs_path / 'objects'
    methods_path = objects_path / 'Global context' / 'methods'

    if not objects_path.exists():
        print(f"Error: Objects directory not found: {objects_path}")
        return False

    if verbose:
        print(f"Scanning FileStorage at: {docs_path}")
        print()

    # Extract functions
    if verbose:
        print("=== Extracting Global Functions ===")
    functions = scan_global_functions(methods_path, verbose)

    if verbose:
        print()
        print("=== Extracting Types ===")
    types = scan_types(objects_path, verbose)

    # Build output structure
    cache_data = {
        "version": "8.3.24",
        "generated": datetime.now().isoformat(),
        "source": str(docs_path),
        "functions": {},
        "types": {}
    }

    # Add functions (keyed by lowercase Russian name for fast lookup)
    for func in functions:
        key = func.name_ru.lower()
        cache_data["functions"][key] = {
            "ru": func.name_ru,
            "en": func.name_en,
            "category": func.category
        }
        # Also add English name as alias
        key_en = func.name_en.lower()
        if key_en != key:
            cache_data["functions"][key_en] = {
                "ru": func.name_ru,
                "en": func.name_en,
                "category": func.category
            }

    # Add types (keyed by lowercase Russian name)
    for typ in types:
        key = typ.name_ru.lower()
        cache_data["types"][key] = {
            "ru": typ.name_ru,
            "en": typ.name_en,
            "category": typ.category
        }
        # Also add English name as alias
        key_en = typ.name_en.lower()
        if key_en != key:
            cache_data["types"][key_en] = {
                "ru": typ.name_ru,
                "en": typ.name_en,
                "category": typ.category
            }

    # Write output
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        if verbose:
            print()
            print("=== Summary ===")
            print(f"Functions extracted: {len(functions)} (+ {len(cache_data['functions']) - len(functions)} English aliases)")
            print(f"Types extracted: {len(types)} (+ {len(cache_data['types']) - len(types)} English aliases)")
            print(f"Output written to: {output_path}")

        return True

    except IOError as e:
        print(f"Error writing output file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate 1C built-ins cache from FileStorage documentation'
    )
    parser.add_argument(
        '--docs-path',
        type=Path,
        default=Path(r'c:\Work\projects\sberdevices\dev\1cbench\extracted_docs\FileStorage'),
        help='Path to FileStorage directory'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path(__file__).parent.parent.parent / 'builtins_cache.json',
        help='Output JSON file path'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose progress information'
    )

    args = parser.parse_args()

    if not args.docs_path.exists():
        print(f"Error: Documentation path not found: {args.docs_path}")
        sys.exit(1)

    success = generate_cache(args.docs_path, args.output, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
