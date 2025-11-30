# -*- coding: utf-8 -*-
"""
Built-in 1C functions and types registry.

This module provides access to 1C:Enterprise platform built-in functions and types
for semantic analysis.
"""

from .registry import (
    BuiltinRegistry,
    is_builtin_function,
    is_builtin_type,
    get_builtin_functions,
    get_builtin_types,
)

__all__ = [
    'BuiltinRegistry',
    'is_builtin_function',
    'is_builtin_type',
    'get_builtin_functions',
    'get_builtin_types',
]
