"""
Abstract Syntax Tree (AST) node definitions for 1C language.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ASTNode:
    """
    Base class for all AST nodes.

    Attributes:
        line: Line number in source code (1-indexed)
        column: Column number in source code (1-indexed)
    """
    line: int = 0
    column: int = 0

    def __repr__(self) -> str:
        """String representation for debugging."""
        class_name = self.__class__.__name__
        fields = []
        for key, value in self.__dict__.items():
            if key not in ['line', 'column']:
                fields.append(f"{key}={value!r}")
        return f"{class_name}({', '.join(fields)})"


# ============================================================================
# Program Structure
# ============================================================================

@dataclass
class ModuleNode(ASTNode):
    """
    Root node representing a 1C module.

    Attributes:
        var_declarations: List of module-level variable declarations
        functions: List of function definitions
        procedures: List of procedure definitions
        statements: List of module-level statements (executed at module load)
    """
    var_declarations: list[VarDeclarationNode] = field(default_factory=list)
    functions: list[FunctionNode] = field(default_factory=list)
    procedures: list[ProcedureNode] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)


# ============================================================================
# Declarations
# ============================================================================

@dataclass
class VarDeclarationNode(ASTNode):
    """
    Variable declaration (Перем).

    Attributes:
        names: List of variable names being declared
    """
    names: list[str] = field(default_factory=list)


@dataclass
class ParameterNode(ASTNode):
    """
    Function/procedure parameter.

    Attributes:
        name: Parameter name
        default_value: Optional default value expression
        by_val: Whether parameter is passed by value (Знач)
    """
    name: str = ""
    default_value: Expression | None = None
    by_val: bool = False


# ============================================================================
# Functions and Procedures
# ============================================================================

@dataclass
class FunctionNode(ASTNode):
    """
    Function definition (Функция ... КонецФункции).

    Attributes:
        name: Function name
        parameters: List of parameters
        body: List of statements in function body
        is_export: Whether function is exported (Экспорт)
        is_async: Whether function is async (Асинх)
        annotation: Optional annotation (&НаСервере, &НаКлиенте, etc.)
    """
    name: str = ""
    parameters: list[ParameterNode] = field(default_factory=list)
    body: list[Statement] = field(default_factory=list)
    is_export: bool = False
    is_async: bool = False
    annotation: str | None = None


@dataclass
class ProcedureNode(ASTNode):
    """
    Procedure definition (Процедура ... КонецПроцедуры).

    Attributes:
        name: Procedure name
        parameters: List of parameters
        body: List of statements in procedure body
        is_export: Whether procedure is exported (Экспорт)
        is_async: Whether procedure is async (Асинх)
        annotation: Optional annotation (&НаСервере, &НаКлиенте, etc.)
    """
    name: str = ""
    parameters: list[ParameterNode] = field(default_factory=list)
    body: list[Statement] = field(default_factory=list)
    is_export: bool = False
    is_async: bool = False
    annotation: str | None = None


# ============================================================================
# Statements
# ============================================================================

Statement = ASTNode  # Type alias for statements


@dataclass
class AssignmentNode(ASTNode):
    """
    Assignment statement (target = value).

    Attributes:
        target: Left-hand side expression (variable, member access, etc.)
        value: Right-hand side expression
    """
    target: Expression = None
    value: Expression = None


@dataclass
class IfNode(ASTNode):
    """
    If statement (Если ... Тогда ... ИначеЕсли ... Иначе ... КонецЕсли).

    Attributes:
        condition: Main condition expression
        then_body: Statements to execute if condition is true
        elif_branches: List of (condition, body) tuples for ИначеЕсли branches
        else_body: Optional statements for Иначе branch
    """
    condition: Expression = None
    then_body: list[Statement] = field(default_factory=list)
    elif_branches: list[tuple[Expression, list[Statement]]] = field(default_factory=list)
    else_body: list[Statement] | None = None


@dataclass
class WhileNode(ASTNode):
    """
    While loop (Пока ... Цикл ... КонецЦикла).

    Attributes:
        condition: Loop condition expression
        body: Statements in loop body
    """
    condition: Expression = None
    body: list[Statement] = field(default_factory=list)


@dataclass
class ForNode(ASTNode):
    """
    Numeric for loop (Для variable = start По end Цикл ... КонецЦикла).

    Attributes:
        variable: Loop variable name
        start: Starting value expression
        end: Ending value expression
        body: Statements in loop body
    """
    variable: str = ""
    start: Expression = None
    end: Expression = None
    body: list[Statement] = field(default_factory=list)


@dataclass
class ForEachNode(ASTNode):
    """
    For-each loop (Для Каждого variable Из collection Цикл ... КонецЦикла).

    Attributes:
        variable: Loop variable name
        collection: Collection expression to iterate over
        body: Statements in loop body
    """
    variable: str = ""
    collection: Expression = None
    body: list[Statement] = field(default_factory=list)


@dataclass
class TryNode(ASTNode):
    """
    Try-catch statement (Попытка ... Исключение ... КонецПопытки).

    Attributes:
        try_body: Statements in try block
        except_body: Statements in exception handler
    """
    try_body: list[Statement] = field(default_factory=list)
    except_body: list[Statement] = field(default_factory=list)


@dataclass
class ReturnNode(ASTNode):
    """
    Return statement (Возврат [value]).

    Attributes:
        value: Optional value to return
    """
    value: Expression | None = None


@dataclass
class BreakNode(ASTNode):
    """Break statement (Прервать)."""
    pass


@dataclass
class ContinueNode(ASTNode):
    """Continue statement (Продолжить)."""
    pass


@dataclass
class RaiseNode(ASTNode):
    """
    Raise exception statement (ВызватьИсключение expression).

    Attributes:
        expression: Expression to raise
    """
    expression: Expression = None


@dataclass
class AwaitNode(ASTNode):
    """
    Await statement (Ждать expression).

    Attributes:
        expression: Expression to await
    """
    expression: Expression = None


@dataclass
class ExpressionStatementNode(ASTNode):
    """
    Expression used as a statement (e.g., function call).

    Attributes:
        expression: The expression being executed
    """
    expression: Expression = None


# ============================================================================
# Expressions
# ============================================================================

Expression = ASTNode  # Type alias for expressions


@dataclass
class BinaryOpNode(ASTNode):
    """
    Binary operation (left operator right).

    Attributes:
        left: Left operand expression
        operator: Operator string (+, -, *, /, =, <>, <, >, И, ИЛИ, etc.)
        right: Right operand expression
    """
    left: Expression = None
    operator: str = ""
    right: Expression = None


@dataclass
class TernaryNode(ASTNode):
    """
    Ternary conditional expression ?(condition, true_value, false_value).

    Attributes:
        condition: Condition expression
        true_value: Value if condition is true
        false_value: Value if condition is false
    """
    condition: Expression = None
    true_value: Expression = None
    false_value: Expression = None


@dataclass
class UnaryOpNode(ASTNode):
    """
    Unary operation (operator operand).

    Attributes:
        operator: Operator string (НЕ, -)
        operand: Operand expression
    """
    operator: str = ""
    operand: Expression = None


@dataclass
class CallNode(ASTNode):
    """
    Function/method call (function(args...)).

    Attributes:
        function: Expression evaluating to callable (identifier or member access)
        arguments: List of argument expressions
    """
    function: Expression = None
    arguments: list[Expression] = field(default_factory=list)


@dataclass
class MemberAccessNode(ASTNode):
    """
    Member access (object.member).

    Attributes:
        object: Object expression
        member: Member name (string)
    """
    object: Expression = None
    member: str = ""


@dataclass
class IndexAccessNode(ASTNode):
    """
    Index access (object[index]).

    Attributes:
        object: Object expression
        index: Index expression
    """
    object: Expression = None
    index: Expression = None


@dataclass
class NewNode(ASTNode):
    """
    Object creation (Новый TypeName(args...)).

    Attributes:
        type_name: Name of type to create
        arguments: List of constructor arguments
    """
    type_name: str = ""
    arguments: list[Expression] = field(default_factory=list)


@dataclass
class IdentifierNode(ASTNode):
    """
    Identifier (variable name, function name, etc.).

    Attributes:
        name: Identifier name
    """
    name: str = ""


@dataclass
class LiteralNode(ASTNode):
    """
    Literal value (string, number, boolean, undefined, date).

    Attributes:
        value: The literal value (str, int, float, bool, None)
        literal_type: Type of literal ("string", "number", "boolean", "undefined", "date")
    """
    value: Any = None
    literal_type: str = ""


# ============================================================================
# AST Visitor Pattern
# ============================================================================

class ASTVisitor:
    """
    Base class for AST visitors.

    Subclass this to implement tree traversal and analysis.
    """

    def visit(self, node: ASTNode):
        """Visit a node and dispatch to appropriate method."""
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode):
        """Default visitor - visits all child nodes."""
        for field_name, field_value in node.__dict__.items():
            if isinstance(field_value, ASTNode):
                self.visit(field_value)
            elif isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, ASTNode):
                        self.visit(item)
                    elif isinstance(item, tuple):
                        for sub_item in item:
                            if isinstance(sub_item, ASTNode):
                                self.visit(sub_item)
                            elif isinstance(sub_item, list):
                                for sub_sub_item in sub_item:
                                    if isinstance(sub_sub_item, ASTNode):
                                        self.visit(sub_sub_item)


# ============================================================================
# AST Pretty Printer
# ============================================================================

class ASTPrettyPrinter(ASTVisitor):
    """Pretty printer for AST nodes."""

    def __init__(self):
        self.indent_level = 0
        self.output = []

    def indent(self):
        """Increase indentation."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indentation."""
        self.indent_level = max(0, self.indent_level - 1)

    def print_line(self, text: str):
        """Print a line with current indentation."""
        self.output.append("  " * self.indent_level + text)

    def print_ast(self, node: ASTNode) -> str:
        """Print AST and return as string."""
        self.output = []
        self.visit(node)
        return "\n".join(self.output)

    def visit_ModuleNode(self, node: ModuleNode):
        self.print_line("Module")
        self.indent()

        if node.var_declarations:
            self.print_line("Variable Declarations:")
            self.indent()
            for var_decl in node.var_declarations:
                self.visit(var_decl)
            self.dedent()

        if node.functions:
            self.print_line("Functions:")
            self.indent()
            for func in node.functions:
                self.visit(func)
            self.dedent()

        if node.procedures:
            self.print_line("Procedures:")
            self.indent()
            for proc in node.procedures:
                self.visit(proc)
            self.dedent()

        self.dedent()

    def visit_VarDeclarationNode(self, node: VarDeclarationNode):
        self.print_line(f"Var: {', '.join(node.names)}")

    def visit_FunctionNode(self, node: FunctionNode):
        export_str = " [Export]" if node.is_export else ""
        async_str = " [Async]" if node.is_async else ""
        annotation_str = f" {node.annotation}" if node.annotation else ""
        params = ", ".join(p.name for p in node.parameters)
        self.print_line(f"Function {node.name}({params}){export_str}{async_str}{annotation_str}")
        self.indent()
        for stmt in node.body:
            self.visit(stmt)
        self.dedent()

    def visit_ProcedureNode(self, node: ProcedureNode):
        export_str = " [Export]" if node.is_export else ""
        async_str = " [Async]" if node.is_async else ""
        annotation_str = f" {node.annotation}" if node.annotation else ""
        params = ", ".join(p.name for p in node.parameters)
        self.print_line(f"Procedure {node.name}({params}){export_str}{async_str}{annotation_str}")
        self.indent()
        for stmt in node.body:
            self.visit(stmt)
        self.dedent()

    def visit_AssignmentNode(self, node: AssignmentNode):
        self.print_line("Assignment:")
        self.indent()
        self.print_line("Target:")
        self.indent()
        self.visit(node.target)
        self.dedent()
        self.print_line("Value:")
        self.indent()
        self.visit(node.value)
        self.dedent()
        self.dedent()

    def visit_IfNode(self, node: IfNode):
        self.print_line("If:")
        self.indent()
        self.print_line("Condition:")
        self.indent()
        self.visit(node.condition)
        self.dedent()
        self.print_line("Then:")
        self.indent()
        for stmt in node.then_body:
            self.visit(stmt)
        self.dedent()

        for elif_cond, elif_body in node.elif_branches:
            self.print_line("ElseIf:")
            self.indent()
            self.print_line("Condition:")
            self.indent()
            self.visit(elif_cond)
            self.dedent()
            self.print_line("Then:")
            self.indent()
            for stmt in elif_body:
                self.visit(stmt)
            self.dedent()
            self.dedent()

        if node.else_body:
            self.print_line("Else:")
            self.indent()
            for stmt in node.else_body:
                self.visit(stmt)
            self.dedent()

        self.dedent()

    def visit_ReturnNode(self, node: ReturnNode):
        if node.value:
            self.print_line("Return:")
            self.indent()
            self.visit(node.value)
            self.dedent()
        else:
            self.print_line("Return")

    def visit_BinaryOpNode(self, node: BinaryOpNode):
        self.print_line(f"BinaryOp: {node.operator}")
        self.indent()
        self.print_line("Left:")
        self.indent()
        self.visit(node.left)
        self.dedent()
        self.print_line("Right:")
        self.indent()
        self.visit(node.right)
        self.dedent()
        self.dedent()

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        self.print_line(f"UnaryOp: {node.operator}")
        self.indent()
        self.visit(node.operand)
        self.dedent()

    def visit_CallNode(self, node: CallNode):
        self.print_line("Call:")
        self.indent()
        self.print_line("Function:")
        self.indent()
        self.visit(node.function)
        self.dedent()
        if node.arguments:
            self.print_line("Arguments:")
            self.indent()
            for arg in node.arguments:
                self.visit(arg)
            self.dedent()
        self.dedent()

    def visit_MemberAccessNode(self, node: MemberAccessNode):
        self.print_line(f"MemberAccess: .{node.member}")
        self.indent()
        self.visit(node.object)
        self.dedent()

    def visit_NewNode(self, node: NewNode):
        self.print_line(f"New: {node.type_name}")
        if node.arguments:
            self.indent()
            self.print_line("Arguments:")
            self.indent()
            for arg in node.arguments:
                self.visit(arg)
            self.dedent()
            self.dedent()

    def visit_IdentifierNode(self, node: IdentifierNode):
        self.print_line(f"Identifier: {node.name}")

    def visit_LiteralNode(self, node: LiteralNode):
        self.print_line(f"Literal ({node.literal_type}): {node.value!r}")

    def visit_ExpressionStatementNode(self, node: ExpressionStatementNode):
        self.print_line("ExpressionStatement:")
        self.indent()
        self.visit(node.expression)
        self.dedent()

    def visit_ForNode(self, node: ForNode):
        self.print_line(f"For: {node.variable}")
        self.indent()
        self.print_line("Start:")
        self.indent()
        self.visit(node.start)
        self.dedent()
        self.print_line("End:")
        self.indent()
        self.visit(node.end)
        self.dedent()
        self.print_line("Body:")
        self.indent()
        for stmt in node.body:
            self.visit(stmt)
        self.dedent()
        self.dedent()

    def visit_ForEachNode(self, node: ForEachNode):
        self.print_line(f"ForEach: {node.variable}")
        self.indent()
        self.print_line("Collection:")
        self.indent()
        self.visit(node.collection)
        self.dedent()
        self.print_line("Body:")
        self.indent()
        for stmt in node.body:
            self.visit(stmt)
        self.dedent()
        self.dedent()

    def visit_WhileNode(self, node: WhileNode):
        self.print_line("While:")
        self.indent()
        self.print_line("Condition:")
        self.indent()
        self.visit(node.condition)
        self.dedent()
        self.print_line("Body:")
        self.indent()
        for stmt in node.body:
            self.visit(stmt)
        self.dedent()
        self.dedent()

    def visit_TryNode(self, node: TryNode):
        self.print_line("Try:")
        self.indent()
        for stmt in node.try_body:
            self.visit(stmt)
        self.dedent()
        self.print_line("Except:")
        self.indent()
        for stmt in node.except_body:
            self.visit(stmt)
        self.dedent()

    def visit_BreakNode(self, node: BreakNode):
        self.print_line("Break")

    def visit_ContinueNode(self, node: ContinueNode):
        self.print_line("Continue")

    def visit_AwaitNode(self, node: AwaitNode):
        self.print_line("Await:")
        self.indent()
        self.visit(node.expression)
        self.dedent()

    def visit_IndexAccessNode(self, node: IndexAccessNode):
        self.print_line("IndexAccess:")
        self.indent()
        self.print_line("Object:")
        self.indent()
        self.visit(node.object)
        self.dedent()
        self.print_line("Index:")
        self.indent()
        self.visit(node.index)
        self.dedent()
        self.dedent()
