# -*- coding: utf-8 -*-
"""
Registry for 1C built-in functions and types.

Provides fast lookup for built-in symbols loaded from a pre-generated JSON cache.
"""

import json
from pathlib import Path
from typing import Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class BuiltinInfo:
    """Information about a built-in function or type."""
    name_ru: str
    name_en: str
    category: str


class BuiltinRegistry:
    """
    Registry of 1C:Enterprise built-in functions and types.

    Loads data from a pre-generated JSON cache file for fast runtime access.
    """

    def __init__(self):
        self._functions: Dict[str, BuiltinInfo] = {}  # lowercase name -> info
        self._types: Dict[str, BuiltinInfo] = {}  # lowercase name -> info
        self._loaded = False

    def load_from_cache(self, cache_path: Path) -> bool:
        """
        Load built-in definitions from JSON cache file.

        Args:
            cache_path: Path to builtins_cache.json

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load functions
            for name_lower, info in data.get('functions', {}).items():
                self._functions[name_lower] = BuiltinInfo(
                    name_ru=info.get('ru', ''),
                    name_en=info.get('en', ''),
                    category=info.get('category', '')
                )

            # Load types
            for name_lower, info in data.get('types', {}).items():
                self._types[name_lower] = BuiltinInfo(
                    name_ru=info.get('ru', ''),
                    name_en=info.get('en', ''),
                    category=info.get('category', '')
                )

            self._loaded = True
            return True

        except (IOError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to load builtins cache: {e}")
            return False

    def is_builtin_function(self, name: str) -> bool:
        """Check if name is a built-in function (case-insensitive)."""
        return name.lower() in self._functions

    def is_builtin_type(self, name: str) -> bool:
        """Check if name is a built-in type (case-insensitive)."""
        return name.lower() in self._types

    def get_function_info(self, name: str) -> Optional[BuiltinInfo]:
        """Get information about a built-in function."""
        return self._functions.get(name.lower())

    def get_type_info(self, name: str) -> Optional[BuiltinInfo]:
        """Get information about a built-in type."""
        return self._types.get(name.lower())

    def get_all_functions(self) -> Set[str]:
        """Get set of all built-in function names (lowercase)."""
        return set(self._functions.keys())

    def get_all_types(self) -> Set[str]:
        """Get set of all built-in type names (lowercase)."""
        return set(self._types.keys())

    @property
    def function_count(self) -> int:
        """Number of registered built-in functions."""
        return len(self._functions)

    @property
    def type_count(self) -> int:
        """Number of registered built-in types."""
        return len(self._types)

    @property
    def is_loaded(self) -> bool:
        """Whether the registry has been loaded from cache."""
        return self._loaded


# Module-level singleton for convenience
_registry: Optional[BuiltinRegistry] = None


def _get_registry() -> BuiltinRegistry:
    """Get or create the global registry singleton."""
    global _registry
    if _registry is None:
        _registry = BuiltinRegistry()
        # Try to load from default cache location
        default_cache = Path(__file__).parent.parent.parent / 'builtins_cache.json'
        if default_cache.exists():
            _registry.load_from_cache(default_cache)
    return _registry


def is_builtin_function(name: str) -> bool:
    """Check if name is a built-in function (case-insensitive)."""
    return _get_registry().is_builtin_function(name)


def is_builtin_type(name: str) -> bool:
    """Check if name is a built-in type (case-insensitive)."""
    return _get_registry().is_builtin_type(name)


def get_builtin_functions() -> Set[str]:
    """Get set of all built-in function names."""
    return _get_registry().get_all_functions()


def get_builtin_types() -> Set[str]:
    """Get set of all built-in type names."""
    return _get_registry().get_all_types()
