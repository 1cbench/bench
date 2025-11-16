"""
Type system for 1C language type inference.
"""

from .types import (
    Type,
    PrimitiveType,
    ArrayType,
    StructureType,
    FunctionType,
    ObjectType,
    AnyType,
    UnionType,
    NUMBER_TYPE,
    STRING_TYPE,
    DATE_TYPE,
    BOOLEAN_TYPE,
    UNDEFINED_TYPE,
    ANY_TYPE,
)

__all__ = [
    "Type",
    "PrimitiveType",
    "ArrayType",
    "StructureType",
    "FunctionType",
    "ObjectType",
    "AnyType",
    "UnionType",
    "NUMBER_TYPE",
    "STRING_TYPE",
    "DATE_TYPE",
    "BOOLEAN_TYPE",
    "UNDEFINED_TYPE",
    "ANY_TYPE",
]
