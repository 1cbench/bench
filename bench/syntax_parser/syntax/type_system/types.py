"""
Type system definitions for 1C language type inference.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Type:
    """Base class for all types in the type system."""

    def __eq__(self, other) -> bool:
        """Check if two types are equal."""
        return isinstance(other, self.__class__)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}()"

    def is_compatible_with(self, other: 'Type') -> bool:
        """
        Check if this type is compatible with another type.

        Args:
            other: The type to check compatibility with

        Returns:
            True if types are compatible, False otherwise
        """
        # AnyType is compatible with everything
        if isinstance(other, AnyType) or isinstance(self, AnyType):
            return True

        # Same types are compatible
        if self == other:
            return True

        return False


@dataclass
class PrimitiveType(Type):
    """
    Primitive type (Число, Строка, Дата, Булево, Неопределено).

    Attributes:
        name: Name of the primitive type
    """
    name: str = ""

    def __eq__(self, other) -> bool:
        return isinstance(other, PrimitiveType) and self.name == other.name

    def __repr__(self) -> str:
        return f"PrimitiveType({self.name!r})"

    def __hash__(self) -> int:
        return hash(('PrimitiveType', self.name))


@dataclass
class ArrayType(Type):
    """
    Array type (Массив).

    Attributes:
        element_type: Type of elements in the array (None for any)
    """
    element_type: Optional[Type] = None

    def __eq__(self, other) -> bool:
        if not isinstance(other, ArrayType):
            return False
        # If either has no element type specified, consider them compatible
        if self.element_type is None or other.element_type is None:
            return True
        return self.element_type == other.element_type

    def __repr__(self) -> str:
        elem_type = self.element_type if self.element_type else "Any"
        return f"ArrayType({elem_type})"


@dataclass
class StructureType(Type):
    """
    Structure type (Структура).

    Attributes:
        fields: Dictionary mapping field names to their types
    """
    fields: Dict[str, Type] = field(default_factory=dict)

    def __eq__(self, other) -> bool:
        if not isinstance(other, StructureType):
            return False
        # If either has no fields specified, consider them compatible
        if not self.fields or not other.fields:
            return True
        return self.fields == other.fields

    def __repr__(self) -> str:
        if not self.fields:
            return "StructureType()"
        fields_str = ", ".join(f"{k}: {v}" for k, v in self.fields.items())
        return f"StructureType({{{fields_str}}})"

    def has_field(self, name: str) -> bool:
        """Check if structure has a field with given name."""
        return name in self.fields

    def get_field_type(self, name: str) -> Optional[Type]:
        """Get the type of a field by name."""
        return self.fields.get(name)


@dataclass
class FunctionType(Type):
    """
    Function type.

    Attributes:
        parameters: List of parameter types
        return_type: Return type of the function
    """
    parameters: List[Type] = field(default_factory=list)
    return_type: Type = None

    def __eq__(self, other) -> bool:
        if not isinstance(other, FunctionType):
            return False
        return (self.parameters == other.parameters and
                self.return_type == other.return_type)

    def __repr__(self) -> str:
        params = ", ".join(str(p) for p in self.parameters)
        return f"FunctionType([{params}] -> {self.return_type})"


@dataclass
class ObjectType(Type):
    """
    Object type for built-in and user-defined classes.

    Attributes:
        class_name: Name of the class/object type
        methods: Dictionary mapping method names to their function types
        properties: Dictionary mapping property names to their types
    """
    class_name: str = ""
    methods: Dict[str, FunctionType] = field(default_factory=dict)
    properties: Dict[str, Type] = field(default_factory=dict)

    def __eq__(self, other) -> bool:
        if not isinstance(other, ObjectType):
            return False
        return self.class_name == other.class_name

    def __repr__(self) -> str:
        return f"ObjectType({self.class_name!r})"

    def __hash__(self) -> int:
        return hash(('ObjectType', self.class_name))

    def has_method(self, name: str) -> bool:
        """Check if object has a method with given name."""
        return name in self.methods

    def get_method_type(self, name: str) -> Optional[FunctionType]:
        """Get the function type of a method by name."""
        return self.methods.get(name)

    def has_property(self, name: str) -> bool:
        """Check if object has a property with given name."""
        return name in self.properties

    def get_property_type(self, name: str) -> Optional[Type]:
        """Get the type of a property by name."""
        return self.properties.get(name)


class AnyType(Type):
    """Unknown/dynamic type - compatible with everything."""

    def __repr__(self) -> str:
        return "AnyType"

    def is_compatible_with(self, other: Type) -> bool:
        """AnyType is compatible with everything."""
        return True


@dataclass
class UnionType(Type):
    """
    Union of multiple types.

    Attributes:
        types: List of possible types
    """
    types: List[Type] = field(default_factory=list)

    def __eq__(self, other) -> bool:
        if not isinstance(other, UnionType):
            return False
        return set(self.types) == set(other.types)

    def __repr__(self) -> str:
        types_str = " | ".join(str(t) for t in self.types)
        return f"UnionType({types_str})"

    def is_compatible_with(self, other: Type) -> bool:
        """Check if any of the union types is compatible with other."""
        return any(t.is_compatible_with(other) for t in self.types)


# ============================================================================
# Common type instances
# ============================================================================

# Primitive types
NUMBER_TYPE = PrimitiveType("Число")
STRING_TYPE = PrimitiveType("Строка")
DATE_TYPE = PrimitiveType("Дата")
BOOLEAN_TYPE = PrimitiveType("Булево")
UNDEFINED_TYPE = PrimitiveType("Неопределено")

# Dynamic type
ANY_TYPE = AnyType()
