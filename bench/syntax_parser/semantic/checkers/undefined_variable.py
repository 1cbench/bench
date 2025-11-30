"""
Checker for undefined variable references in 1C code.

This module provides two visitor classes:
1. VariableCollector: Collects all variable declarations and builds the symbol table
2. UndefinedVariableChecker: Checks all variable references against the symbol table
"""

from typing import List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from syntax.parser.ast_nodes import (
    ASTNode, ASTVisitor, ModuleNode, FunctionNode, ProcedureNode,
    VarDeclarationNode, ForNode, ForEachNode, IdentifierNode,
    AssignmentNode, BinaryOpNode, UnaryOpNode, CallNode,
    MemberAccessNode, IndexAccessNode, ReturnNode, IfNode,
    WhileNode, TryNode, ExpressionStatementNode, BreakNode,
    ContinueNode, AwaitNode, NewNode, LiteralNode
)
from ..symbol_table import Symbol, SymbolTable
from ..errors import SemanticError


class VariableCollector(ASTVisitor):
    """
    Collects all variable declarations and builds the symbol table.

    This visitor traverses the AST and collects:
    - Module-level variable declarations
    - Function/procedure parameters
    - Function/procedure local variables
    - Loop variables (Для, Для Каждого)
    """

    def __init__(self, builtins=None):
        """
        Initialize the collector with a symbol table.

        Args:
            builtins: Optional BuiltinRegistry to pre-populate with built-in functions and types
        """
        self.symbol_table = SymbolTable(builtins=builtins)

    def visit_ModuleNode(self, node: ModuleNode):
        """
        Visit module node - process module-level variables and functions/procedures.
        """
        # Collect module-level variable declarations
        for var_decl in node.var_declarations:
            self.visit(var_decl)

        # First pass: declare all functions and procedures in module scope
        for func in node.functions:
            self.symbol_table.define(
                func.name,
                Symbol(
                    name=func.name,
                    kind='function',
                    line=func.line,
                    column=func.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

        for proc in node.procedures:
            self.symbol_table.define(
                proc.name,
                Symbol(
                    name=proc.name,
                    kind='procedure',
                    line=proc.line,
                    column=proc.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

        # Second pass: process function and procedure bodies
        for func in node.functions:
            self.visit(func)

        for proc in node.procedures:
            self.visit(proc)

    def visit_VarDeclarationNode(self, node: VarDeclarationNode):
        """
        Visit variable declaration node - add variables to current scope.
        """
        for var_name in node.names:
            self.symbol_table.define(
                var_name,
                Symbol(
                    name=var_name,
                    kind='variable',
                    line=node.line,
                    column=node.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

    def visit_FunctionNode(self, node: FunctionNode):
        """
        Visit function node - enter function scope and collect parameters and local vars.
        """
        # Enter function scope
        self.symbol_table.enter_scope()

        # Add parameters to function scope
        for param in node.parameters:
            self.symbol_table.define(
                param.name,
                Symbol(
                    name=param.name,
                    kind='parameter',
                    line=param.line,
                    column=param.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

        # Process function body to collect local variables
        for stmt in node.body:
            # Only collect variable declarations, not execute statements
            if isinstance(stmt, VarDeclarationNode):
                self.visit(stmt)
            elif isinstance(stmt, (ForNode, ForEachNode)):
                # Visit loop nodes to collect loop variables
                self.visit(stmt)
            # Recursively check nested structures for variable declarations
            elif hasattr(stmt, 'body'):
                self._collect_vars_from_body(stmt)

        # Exit function scope
        self.symbol_table.exit_scope()

    def visit_ProcedureNode(self, node: ProcedureNode):
        """
        Visit procedure node - enter procedure scope and collect parameters and local vars.
        """
        # Enter procedure scope
        self.symbol_table.enter_scope()

        # Add parameters to procedure scope
        for param in node.parameters:
            self.symbol_table.define(
                param.name,
                Symbol(
                    name=param.name,
                    kind='parameter',
                    line=param.line,
                    column=param.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

        # Process procedure body to collect local variables
        for stmt in node.body:
            # Only collect variable declarations, not execute statements
            if isinstance(stmt, VarDeclarationNode):
                self.visit(stmt)
            elif isinstance(stmt, (ForNode, ForEachNode)):
                # Visit loop nodes to collect loop variables
                self.visit(stmt)
            # Recursively check nested structures for variable declarations
            elif hasattr(stmt, 'body'):
                self._collect_vars_from_body(stmt)

        # Exit procedure scope
        self.symbol_table.exit_scope()

    def visit_ForNode(self, node: ForNode):
        """
        Visit for loop node - define loop variable in current scope.

        Note: In 1C, loop variables are function-scoped, not block-scoped.
        """
        # Define loop variable
        self.symbol_table.define(
            node.variable,
            Symbol(
                name=node.variable,
                kind='loop_variable',
                line=node.line,
                column=node.column,
                scope_level=self.symbol_table.get_current_scope_level()
            )
        )

        # Collect variables from loop body
        for stmt in node.body:
            if isinstance(stmt, VarDeclarationNode):
                self.visit(stmt)
            elif isinstance(stmt, (ForNode, ForEachNode)):
                self.visit(stmt)
            elif hasattr(stmt, 'body'):
                self._collect_vars_from_body(stmt)

    def visit_ForEachNode(self, node: ForEachNode):
        """
        Visit for-each loop node - define loop variable in current scope.

        Note: In 1C, loop variables are function-scoped, not block-scoped.
        """
        # Define loop variable
        self.symbol_table.define(
            node.variable,
            Symbol(
                name=node.variable,
                kind='loop_variable',
                line=node.line,
                column=node.column,
                scope_level=self.symbol_table.get_current_scope_level()
            )
        )

        # Collect variables from loop body
        for stmt in node.body:
            if isinstance(stmt, VarDeclarationNode):
                self.visit(stmt)
            elif isinstance(stmt, (ForNode, ForEachNode)):
                self.visit(stmt)
            elif hasattr(stmt, 'body'):
                self._collect_vars_from_body(stmt)

    def _collect_vars_from_body(self, node: ASTNode):
        """
        Helper method to recursively collect variable declarations from nested structures.
        """
        if isinstance(node, IfNode):
            # Check then body
            for stmt in node.then_body:
                if isinstance(stmt, VarDeclarationNode):
                    self.visit(stmt)
                elif isinstance(stmt, (ForNode, ForEachNode)):
                    self.visit(stmt)
                elif hasattr(stmt, 'body'):
                    self._collect_vars_from_body(stmt)

            # Check elif branches
            for _, elif_body in node.elif_branches:
                for stmt in elif_body:
                    if isinstance(stmt, VarDeclarationNode):
                        self.visit(stmt)
                    elif isinstance(stmt, (ForNode, ForEachNode)):
                        self.visit(stmt)
                    elif hasattr(stmt, 'body'):
                        self._collect_vars_from_body(stmt)

            # Check else body
            if node.else_body:
                for stmt in node.else_body:
                    if isinstance(stmt, VarDeclarationNode):
                        self.visit(stmt)
                    elif isinstance(stmt, (ForNode, ForEachNode)):
                        self.visit(stmt)
                    elif hasattr(stmt, 'body'):
                        self._collect_vars_from_body(stmt)

        elif isinstance(node, WhileNode):
            for stmt in node.body:
                if isinstance(stmt, VarDeclarationNode):
                    self.visit(stmt)
                elif isinstance(stmt, (ForNode, ForEachNode)):
                    self.visit(stmt)
                elif hasattr(stmt, 'body'):
                    self._collect_vars_from_body(stmt)

        elif isinstance(node, TryNode):
            for stmt in node.try_body:
                if isinstance(stmt, VarDeclarationNode):
                    self.visit(stmt)
                elif isinstance(stmt, (ForNode, ForEachNode)):
                    self.visit(stmt)
                elif hasattr(stmt, 'body'):
                    self._collect_vars_from_body(stmt)

            for stmt in node.except_body:
                if isinstance(stmt, VarDeclarationNode):
                    self.visit(stmt)
                elif isinstance(stmt, (ForNode, ForEachNode)):
                    self.visit(stmt)
                elif hasattr(stmt, 'body'):
                    self._collect_vars_from_body(stmt)


class UndefinedVariableChecker(ASTVisitor):
    """
    Checks all variable references against the symbol table.

    Reports errors for:
    - Undefined variable references
    - Variables used before declaration (in some contexts)
    """

    def __init__(self, symbol_table: SymbolTable):
        """
        Initialize the checker with a pre-populated symbol table.

        Args:
            symbol_table: Symbol table containing all variable declarations
        """
        self.symbol_table = symbol_table
        self.errors: List[SemanticError] = []

    def visit_ModuleNode(self, node: ModuleNode):
        """Visit module node and check all functions/procedures."""
        # Check all functions
        for func in node.functions:
            self.visit(func)

        # Check all procedures
        for proc in node.procedures:
            self.visit(proc)

    def visit_FunctionNode(self, node: FunctionNode):
        """Visit function node - enter scope and check body."""
        self.symbol_table.enter_scope()

        # Re-add parameters to match the structure from VariableCollector
        for param in node.parameters:
            self.symbol_table.define(
                param.name,
                Symbol(
                    name=param.name,
                    kind='parameter',
                    line=param.line,
                    column=param.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

        # Re-collect local variables to match scope structure
        self._recollect_local_vars(node.body)

        # Check function body
        for stmt in node.body:
            self.visit(stmt)

        self.symbol_table.exit_scope()

    def visit_ProcedureNode(self, node: ProcedureNode):
        """Visit procedure node - enter scope and check body."""
        self.symbol_table.enter_scope()

        # Re-add parameters to match the structure from VariableCollector
        for param in node.parameters:
            self.symbol_table.define(
                param.name,
                Symbol(
                    name=param.name,
                    kind='parameter',
                    line=param.line,
                    column=param.column,
                    scope_level=self.symbol_table.get_current_scope_level()
                )
            )

        # Re-collect local variables to match scope structure
        self._recollect_local_vars(node.body)

        # Check procedure body
        for stmt in node.body:
            self.visit(stmt)

        self.symbol_table.exit_scope()

    def _recollect_local_vars(self, body: List[ASTNode]):
        """Helper to re-collect local variables in current scope."""
        for stmt in body:
            if isinstance(stmt, VarDeclarationNode):
                for var_name in stmt.names:
                    self.symbol_table.define(
                        var_name,
                        Symbol(
                            name=var_name,
                            kind='variable',
                            line=stmt.line,
                            column=stmt.column,
                            scope_level=self.symbol_table.get_current_scope_level()
                        )
                    )
            elif isinstance(stmt, ForNode):
                self.symbol_table.define(
                    stmt.variable,
                    Symbol(
                        name=stmt.variable,
                        kind='loop_variable',
                        line=stmt.line,
                        column=stmt.column,
                        scope_level=self.symbol_table.get_current_scope_level()
                    )
                )
                self._recollect_local_vars(stmt.body)
            elif isinstance(stmt, ForEachNode):
                self.symbol_table.define(
                    stmt.variable,
                    Symbol(
                        name=stmt.variable,
                        kind='loop_variable',
                        line=stmt.line,
                        column=stmt.column,
                        scope_level=self.symbol_table.get_current_scope_level()
                    )
                )
                self._recollect_local_vars(stmt.body)
            elif isinstance(stmt, IfNode):
                self._recollect_local_vars(stmt.then_body)
                for _, elif_body in stmt.elif_branches:
                    self._recollect_local_vars(elif_body)
                if stmt.else_body:
                    self._recollect_local_vars(stmt.else_body)
            elif isinstance(stmt, WhileNode):
                self._recollect_local_vars(stmt.body)
            elif isinstance(stmt, TryNode):
                self._recollect_local_vars(stmt.try_body)
                self._recollect_local_vars(stmt.except_body)

    def visit_IdentifierNode(self, node: IdentifierNode):
        """
        Visit identifier node - check if variable is defined.

        Skip checking if this identifier is part of a member access (object.member)
        or a function call, as those are handled separately.
        """
        # Look up the identifier in symbol table
        symbol = self.symbol_table.lookup(node.name)

        if symbol is None:
            # Variable is not defined
            self.errors.append(
                SemanticError(
                    message=f"Undefined variable '{node.name}'",
                    line=node.line,
                    column=node.column,
                    error_type='undefined_variable'
                )
            )

    def visit_AssignmentNode(self, node: AssignmentNode):
        """Visit assignment node - check both target and value."""
        # For assignment target, we need special handling
        # If target is a simple identifier, it might be a new assignment
        # If target is member access or index access, check the base object

        # IMPORTANT: Check value FIRST before defining target variable
        # This ensures RHS variables are checked before LHS is defined
        if node.value:
            self.visit(node.value)

        if isinstance(node.target, IdentifierNode):
            # In 1C, assignment implicitly declares the variable
            # So we define it if not already defined
            symbol = self.symbol_table.lookup(node.target.name)
            if symbol is None:
                # Implicitly define the variable
                self.symbol_table.define(
                    node.target.name,
                    Symbol(
                        name=node.target.name,
                        kind='variable',
                        line=node.target.line,
                        column=node.target.column,
                        scope_level=self.symbol_table.get_current_scope_level()
                    )
                )
        else:
            # For member access or index access, visit normally
            self.visit(node.target)

    def visit_BinaryOpNode(self, node: BinaryOpNode):
        """Visit binary operation - check both operands."""
        if node.left:
            self.visit(node.left)
        if node.right:
            self.visit(node.right)

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        """Visit unary operation - check operand."""
        if node.operand:
            self.visit(node.operand)

    def visit_CallNode(self, node: CallNode):
        """Visit call node - check function and arguments."""
        # Check the function expression (could be identifier or member access)
        if isinstance(node.function, IdentifierNode):
            # Check if function is defined
            symbol = self.symbol_table.lookup(node.function.name)
            if symbol is None:
                self.errors.append(
                    SemanticError(
                        message=f"Call to undefined function '{node.function.name}'",
                        line=node.function.line,
                        column=node.function.column,
                        error_type='undefined_variable'
                    )
                )
        else:
            # For member access, check the object
            self.visit(node.function)

        # Check all arguments
        for arg in node.arguments:
            self.visit(arg)

    def visit_MemberAccessNode(self, node: MemberAccessNode):
        """Visit member access node - only check the object, not the member."""
        # Only check the object part, not the member name
        # (member validation is for Phase 2)
        if node.object:
            self.visit(node.object)

    def visit_IndexAccessNode(self, node: IndexAccessNode):
        """Visit index access node - check object and index."""
        if node.object:
            self.visit(node.object)
        if node.index:
            self.visit(node.index)

    def visit_ReturnNode(self, node: ReturnNode):
        """Visit return node - check return value."""
        if node.value:
            self.visit(node.value)

    def visit_IfNode(self, node: IfNode):
        """Visit if node - check condition and all branches."""
        # Check condition
        if node.condition:
            self.visit(node.condition)

        # Check then body
        for stmt in node.then_body:
            self.visit(stmt)

        # Check elif branches
        for elif_cond, elif_body in node.elif_branches:
            if elif_cond:
                self.visit(elif_cond)
            for stmt in elif_body:
                self.visit(stmt)

        # Check else body
        if node.else_body:
            for stmt in node.else_body:
                self.visit(stmt)

    def visit_WhileNode(self, node: WhileNode):
        """Visit while node - check condition and body."""
        if node.condition:
            self.visit(node.condition)

        for stmt in node.body:
            self.visit(stmt)

    def visit_ForNode(self, node: ForNode):
        """Visit for node - check start, end, and body."""
        # Check start and end expressions
        if node.start:
            self.visit(node.start)
        if node.end:
            self.visit(node.end)

        # Check body
        for stmt in node.body:
            self.visit(stmt)

    def visit_ForEachNode(self, node: ForEachNode):
        """Visit for-each node - check collection and body."""
        # Check collection expression
        if node.collection:
            self.visit(node.collection)

        # Check body
        for stmt in node.body:
            self.visit(stmt)

    def visit_TryNode(self, node: TryNode):
        """Visit try node - check try and except bodies."""
        for stmt in node.try_body:
            self.visit(stmt)

        for stmt in node.except_body:
            self.visit(stmt)

    def visit_ExpressionStatementNode(self, node: ExpressionStatementNode):
        """Visit expression statement - check the expression."""
        if node.expression:
            self.visit(node.expression)

    def visit_NewNode(self, node: NewNode):
        """Visit new node - check type name and constructor arguments."""
        # Check if the type is defined (built-in type or user-defined)
        if node.type_name:
            symbol = self.symbol_table.lookup(node.type_name)
            if symbol is None:
                self.errors.append(
                    SemanticError(
                        message=f"Unknown type '{node.type_name}'",
                        line=node.line,
                        column=node.column,
                        error_type='undefined_type'
                    )
                )

        # Check constructor arguments
        for arg in node.arguments:
            self.visit(arg)

    def visit_LiteralNode(self, node: LiteralNode):
        """Visit literal node - nothing to check."""
        pass

    def visit_BreakNode(self, node: BreakNode):
        """Visit break node - nothing to check."""
        pass

    def visit_ContinueNode(self, node: ContinueNode):
        """Visit continue node - nothing to check."""
        pass

    def visit_AwaitNode(self, node: AwaitNode):
        """Visit await node - check expression."""
        if node.expression:
            self.visit(node.expression)

    def visit_VarDeclarationNode(self, node: VarDeclarationNode):
        """Visit variable declaration - nothing to check."""
        pass
