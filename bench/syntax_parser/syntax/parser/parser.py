"""
Parser implementation for 1C language using recursive descent parsing.

This module provides the Parser class that builds an AST from a token stream.
"""

from __future__ import annotations
from ..lexer import Token, TokenType
from .ast_nodes import *


class ParserError(Exception):
    """Exception raised when parser encounters an error."""
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Parser error at {token.line}:{token.column}: {message}")


# Operator precedence (higher number = higher precedence)
PRECEDENCE = {
    'ИЛИ': 1,
    'И': 2,
    'НЕ': 3,
    '=': 4, '<>': 4, '<': 4, '>': 4, '<=': 4, '>=': 4,
    '+': 5, '-': 5,
    '*': 6, '/': 6, '%': 6,
}


class Parser:
    """
    Recursive descent parser for 1C language.

    Converts a stream of tokens into an Abstract Syntax Tree (AST).
    """

    def __init__(self, tokens: list[Token]):
        """
        Initialize parser with token stream.

        Args:
            tokens: List of tokens from lexer
        """
        self.tokens = tokens
        self.current = 0
        self.current_annotation = None  # Track current annotation (&НаСервере, etc.)

    # ==================== Helper Methods ====================

    def peek(self, offset: int = 0) -> Token:
        """
        Look ahead at token without consuming it.

        Args:
            offset: Number of tokens to look ahead (0 = current)

        Returns:
            Token at current + offset position, or EOF if past end
        """
        pos = self.current + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[pos]

    def advance(self) -> Token:
        """
        Consume and return current token.

        Returns:
            Current token before advancing
        """
        token = self.peek()
        if token.type != TokenType.EOF:
            self.current += 1
        return token

    def expect(self, token_type: TokenType, message: str | None = None) -> Token:
        """
        Consume current token and verify it matches expected type.

        Args:
            token_type: Expected token type
            message: Optional custom error message

        Returns:
            The consumed token

        Raises:
            ParserError: If token doesn't match expected type
        """
        token = self.peek()
        if token.type != token_type:
            if message:
                raise ParserError(message, token)
            else:
                raise ParserError(f"Expected {token_type.name}, got {token.type.name}", token)
        return self.advance()

    def match(self, *token_types: TokenType) -> bool:
        """
        Check if current token matches any of the given types.

        Args:
            token_types: Token types to check

        Returns:
            True if current token matches any type
        """
        return self.peek().type in token_types

    def skip_newlines(self):
        """Skip any newline and comment tokens."""
        while self.match(TokenType.NEWLINE, TokenType.COMMENT):
            self.advance()

    def synchronize(self):
        """
        Synchronize parser after error by advancing to next statement boundary.
        Used for error recovery.
        """
        self.advance()

        while not self.match(TokenType.EOF):
            if self.peek(-1).type == TokenType.DELIMITER_SEMICOLON:
                return

            if self.match(
                TokenType.KEYWORD_FUNCTION,
                TokenType.KEYWORD_PROCEDURE,
                TokenType.KEYWORD_IF,
                TokenType.KEYWORD_FOR,
                TokenType.KEYWORD_WHILE,
                TokenType.KEYWORD_RETURN,
                TokenType.KEYWORD_VAR
            ):
                return

            self.advance()

    # ==================== Main Parse Method ====================

    def parse(self) -> ModuleNode:
        """
        Parse token stream into AST.

        Returns:
            ModuleNode representing the entire module

        Raises:
            ParserError: If syntax errors are encountered
        """
        return self.parse_module()

    # ==================== Module Level ====================

    def parse_module(self) -> ModuleNode:
        """
        Parse a complete 1C module.

        Grammar:
            module = (annotation | var_declaration | function | procedure)*
        """
        module = ModuleNode()
        self.skip_newlines()

        while not self.match(TokenType.EOF):
            self.skip_newlines()

            # Check for annotations
            if self.match(TokenType.ANNOTATION):
                self.current_annotation = self.advance().value
                self.skip_newlines()
                continue

            # Variable declaration
            if self.match(TokenType.KEYWORD_VAR):
                var_decl = self.parse_var_declaration()
                module.var_declarations.append(var_decl)
                self.current_annotation = None

            # Function declaration
            elif self.match(TokenType.KEYWORD_ASYNC):
                # Could be async function or procedure
                self.advance()  # consume Асинх
                self.skip_newlines()

                if self.match(TokenType.KEYWORD_FUNCTION):
                    func = self.parse_function()
                    func.is_async = True
                    func.annotation = self.current_annotation
                    module.functions.append(func)
                elif self.match(TokenType.KEYWORD_PROCEDURE):
                    proc = self.parse_procedure()
                    proc.is_async = True
                    proc.annotation = self.current_annotation
                    module.procedures.append(proc)
                else:
                    raise ParserError("Expected Функция or Процедура after Асинх", self.peek())

                self.current_annotation = None

            elif self.match(TokenType.KEYWORD_FUNCTION):
                func = self.parse_function()
                func.annotation = self.current_annotation
                module.functions.append(func)
                self.current_annotation = None

            # Procedure declaration
            elif self.match(TokenType.KEYWORD_PROCEDURE):
                proc = self.parse_procedure()
                proc.annotation = self.current_annotation
                module.procedures.append(proc)
                self.current_annotation = None

            # Preprocessor directives (just skip for now)
            elif self.match(TokenType.PREPROCESSOR_IF, TokenType.PREPROCESSOR_ELSE, TokenType.PREPROCESSOR_ENDIF):
                self.advance()

            else:
                # Try to parse as a statement (module-level code)
                token = self.peek()
                if token.type == TokenType.EOF:
                    break
                try:
                    stmt = self.parse_statement()
                    if stmt:
                        module.statements.append(stmt)
                except ParserError:
                    # Re-raise with better context
                    raise ParserError(f"Unexpected token at module level: {token.value}", token)

            self.skip_newlines()

        return module

    def parse_var_declaration(self) -> VarDeclarationNode:
        """
        Parse variable declaration.

        Grammar:
            var_declaration = "Перем" identifier ("," identifier)* ";"
        """
        token = self.expect(TokenType.KEYWORD_VAR)
        node = VarDeclarationNode(line=token.line, column=token.column)

        # Parse first variable name
        name_token = self.expect(TokenType.IDENTIFIER)
        node.names.append(name_token.value)

        # Parse additional variable names
        while self.match(TokenType.DELIMITER_COMMA):
            self.advance()
            self.skip_newlines()
            name_token = self.expect(TokenType.IDENTIFIER)
            node.names.append(name_token.value)

        self.expect(TokenType.DELIMITER_SEMICOLON)
        return node

    # ==================== Functions and Procedures ====================

    def parse_function(self) -> FunctionNode:
        """
        Parse function definition.

        Grammar:
            function = "Функция" identifier "(" parameters? ")" ("Экспорт")? statements "КонецФункции"
        """
        token = self.expect(TokenType.KEYWORD_FUNCTION)
        node = FunctionNode(line=token.line, column=token.column)

        # Function name
        name_token = self.expect(TokenType.IDENTIFIER)
        node.name = name_token.value

        # Parameters
        self.expect(TokenType.DELIMITER_LPAREN)
        if not self.match(TokenType.DELIMITER_RPAREN):
            node.parameters = self.parse_parameters()
        self.expect(TokenType.DELIMITER_RPAREN)

        # Export keyword
        if self.match(TokenType.KEYWORD_EXPORT):
            self.advance()
            node.is_export = True

        self.skip_newlines()

        # Function body
        node.body = self.parse_statement_block(TokenType.KEYWORD_END_FUNCTION)

        self.expect(TokenType.KEYWORD_END_FUNCTION)

        return node

    def parse_procedure(self) -> ProcedureNode:
        """
        Parse procedure definition.

        Grammar:
            procedure = "Процедура" identifier "(" parameters? ")" ("Экспорт")? statements "КонецПроцедуры"
        """
        token = self.expect(TokenType.KEYWORD_PROCEDURE)
        node = ProcedureNode(line=token.line, column=token.column)

        # Procedure name
        name_token = self.expect(TokenType.IDENTIFIER)
        node.name = name_token.value

        # Parameters
        self.expect(TokenType.DELIMITER_LPAREN)
        if not self.match(TokenType.DELIMITER_RPAREN):
            node.parameters = self.parse_parameters()
        self.expect(TokenType.DELIMITER_RPAREN)

        # Export keyword
        if self.match(TokenType.KEYWORD_EXPORT):
            self.advance()
            node.is_export = True

        self.skip_newlines()

        # Procedure body
        node.body = self.parse_statement_block(TokenType.KEYWORD_END_PROCEDURE)

        self.expect(TokenType.KEYWORD_END_PROCEDURE)

        return node

    def parse_parameters(self) -> list[ParameterNode]:
        """
        Parse function/procedure parameters.

        Grammar:
            parameters = parameter ("," parameter)*
            parameter = ("Знач")? identifier ("=" expression)?
        """
        parameters = []

        # First parameter
        by_val = False
        if self.match(TokenType.KEYWORD_VAL):
            self.advance()
            by_val = True

        param_token = self.expect(TokenType.IDENTIFIER)
        param = ParameterNode(name=param_token.value, line=param_token.line, column=param_token.column, by_val=by_val)

        # Default value
        if self.match(TokenType.OP_ASSIGN):
            self.advance()
            param.default_value = self.parse_expression()

        parameters.append(param)

        # Additional parameters
        while self.match(TokenType.DELIMITER_COMMA):
            self.advance()
            self.skip_newlines()

            by_val = False
            if self.match(TokenType.KEYWORD_VAL):
                self.advance()
                by_val = True

            param_token = self.expect(TokenType.IDENTIFIER)
            param = ParameterNode(name=param_token.value, line=param_token.line, column=param_token.column, by_val=by_val)

            if self.match(TokenType.OP_ASSIGN):
                self.advance()
                param.default_value = self.parse_expression()

            parameters.append(param)

        return parameters

    # ==================== Statement Parsing ====================

    def parse_statement_block(self, *end_tokens: TokenType) -> list[Statement]:
        """
        Parse a block of statements until one of the end tokens is reached.

        Args:
            end_tokens: Token types that mark the end of the block

        Returns:
            List of statement nodes
        """
        statements = []
        self.skip_newlines()

        while not self.match(*end_tokens, TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()

        return statements

    def parse_statement(self) -> Statement | None:
        """
        Parse a single statement.

        Returns:
            Statement node, or None if no statement found
        """
        self.skip_newlines()

        # Variable declaration
        if self.match(TokenType.KEYWORD_VAR):
            return self.parse_var_declaration()

        # If statement
        if self.match(TokenType.KEYWORD_IF):
            return self.parse_if_statement()

        # While loop
        if self.match(TokenType.KEYWORD_WHILE):
            return self.parse_while_statement()

        # For loop (numeric or for-each)
        if self.match(TokenType.KEYWORD_FOR):
            return self.parse_for_statement()

        # Try-catch
        if self.match(TokenType.KEYWORD_TRY):
            return self.parse_try_statement()

        # Return
        if self.match(TokenType.KEYWORD_RETURN):
            return self.parse_return_statement()

        # Break
        if self.match(TokenType.KEYWORD_BREAK):
            token = self.advance()
            self.expect(TokenType.DELIMITER_SEMICOLON)
            return BreakNode(line=token.line, column=token.column)

        # Continue
        if self.match(TokenType.KEYWORD_CONTINUE):
            token = self.advance()
            self.expect(TokenType.DELIMITER_SEMICOLON)
            return ContinueNode(line=token.line, column=token.column)

        # Raise exception
        if self.match(TokenType.KEYWORD_RAISE):
            return self.parse_raise_statement()

        # Await
        if self.match(TokenType.KEYWORD_AWAIT):
            return self.parse_await_statement()

        # Expression statement or assignment
        if not self.match(TokenType.EOF):
            return self.parse_expression_or_assignment()

        return None

    def parse_if_statement(self) -> IfNode:
        """
        Parse if statement.

        Grammar:
            if_stmt = "Если" expression "Тогда" statements
                     ("ИначеЕсли" expression "Тогда" statements)*
                     ("Иначе" statements)?
                     "КонецЕсли"
        """
        token = self.expect(TokenType.KEYWORD_IF)
        node = IfNode(line=token.line, column=token.column)

        # Main condition
        node.condition = self.parse_expression()
        self.expect(TokenType.KEYWORD_THEN)
        self.skip_newlines()

        # Then body
        node.then_body = self.parse_statement_block(
            TokenType.KEYWORD_ELSE_IF,
            TokenType.KEYWORD_ELSE,
            TokenType.KEYWORD_END_IF
        )

        # ElseIf branches
        while self.match(TokenType.KEYWORD_ELSE_IF):
            self.advance()
            elif_condition = self.parse_expression()
            self.expect(TokenType.KEYWORD_THEN)
            self.skip_newlines()

            elif_body = self.parse_statement_block(
                TokenType.KEYWORD_ELSE_IF,
                TokenType.KEYWORD_ELSE,
                TokenType.KEYWORD_END_IF
            )

            node.elif_branches.append((elif_condition, elif_body))

        # Else branch
        if self.match(TokenType.KEYWORD_ELSE):
            self.advance()
            self.skip_newlines()
            node.else_body = self.parse_statement_block(TokenType.KEYWORD_END_IF)

        self.expect(TokenType.KEYWORD_END_IF)
        self.expect(TokenType.DELIMITER_SEMICOLON)

        return node

    def parse_while_statement(self) -> WhileNode:
        """
        Parse while loop.

        Grammar:
            while_stmt = "Пока" expression "Цикл" statements "КонецЦикла"
        """
        token = self.expect(TokenType.KEYWORD_WHILE)
        node = WhileNode(line=token.line, column=token.column)

        node.condition = self.parse_expression()
        self.expect(TokenType.KEYWORD_CYCLE)
        self.skip_newlines()

        node.body = self.parse_statement_block(TokenType.KEYWORD_END_CYCLE)

        self.expect(TokenType.KEYWORD_END_CYCLE)
        self.expect(TokenType.DELIMITER_SEMICOLON)

        return node

    def parse_for_statement(self) -> ForNode | ForEachNode:
        """
        Parse for loop (numeric or for-each).

        Grammar:
            for_stmt = "Для" identifier "=" expression "По" expression "Цикл" statements "КонецЦикла"
            foreach_stmt = "Для" "Каждого" identifier "Из" expression "Цикл" statements "КонецЦикла"
        """
        token = self.expect(TokenType.KEYWORD_FOR)

        # Check for "Каждого" (for-each)
        if self.match(TokenType.KEYWORD_EACH):
            self.advance()

            # For-each loop
            node = ForEachNode(line=token.line, column=token.column)

            var_token = self.expect(TokenType.IDENTIFIER)
            node.variable = var_token.value

            self.expect(TokenType.KEYWORD_FROM)
            node.collection = self.parse_expression()

            self.expect(TokenType.KEYWORD_CYCLE)
            self.skip_newlines()

            node.body = self.parse_statement_block(TokenType.KEYWORD_END_CYCLE)

            self.expect(TokenType.KEYWORD_END_CYCLE)
            self.expect(TokenType.DELIMITER_SEMICOLON)

            return node

        else:
            # Numeric for loop
            node = ForNode(line=token.line, column=token.column)

            var_token = self.expect(TokenType.IDENTIFIER)
            node.variable = var_token.value

            self.expect(TokenType.OP_ASSIGN)
            node.start = self.parse_expression()

            self.expect(TokenType.KEYWORD_TO)
            node.end = self.parse_expression()

            self.expect(TokenType.KEYWORD_CYCLE)
            self.skip_newlines()

            node.body = self.parse_statement_block(TokenType.KEYWORD_END_CYCLE)

            self.expect(TokenType.KEYWORD_END_CYCLE)
            self.expect(TokenType.DELIMITER_SEMICOLON)

            return node

    def parse_try_statement(self) -> TryNode:
        """
        Parse try-catch statement.

        Grammar:
            try_stmt = "Попытка" statements "Исключение" statements "КонецПопытки"
        """
        token = self.expect(TokenType.KEYWORD_TRY)
        node = TryNode(line=token.line, column=token.column)

        self.skip_newlines()

        node.try_body = self.parse_statement_block(TokenType.KEYWORD_EXCEPTION)

        self.expect(TokenType.KEYWORD_EXCEPTION)
        self.skip_newlines()

        node.except_body = self.parse_statement_block(TokenType.KEYWORD_END_TRY)

        self.expect(TokenType.KEYWORD_END_TRY)
        self.expect(TokenType.DELIMITER_SEMICOLON)

        return node

    def parse_return_statement(self) -> ReturnNode:
        """
        Parse return statement.

        Grammar:
            return_stmt = "Возврат" expression? ";"
        """
        token = self.expect(TokenType.KEYWORD_RETURN)
        node = ReturnNode(line=token.line, column=token.column)

        # Check for return value
        if not self.match(TokenType.DELIMITER_SEMICOLON):
            node.value = self.parse_expression()

        self.expect(TokenType.DELIMITER_SEMICOLON)
        return node

    def parse_await_statement(self) -> AwaitNode:
        """
        Parse await statement.

        Grammar:
            await_stmt = "Ждать" expression ";"
        """
        token = self.expect(TokenType.KEYWORD_AWAIT)
        node = AwaitNode(line=token.line, column=token.column)

        node.expression = self.parse_expression()
        self.expect(TokenType.DELIMITER_SEMICOLON)

        return node

    def parse_raise_statement(self) -> RaiseNode:
        """
        Parse raise exception statement.

        Grammar:
            raise_stmt = "ВызватьИсключение" expression? ";"
        """
        token = self.expect(TokenType.KEYWORD_RAISE)
        node = RaiseNode(line=token.line, column=token.column)

        # Expression is optional - if absent, re-raises current exception
        if not self.match(TokenType.DELIMITER_SEMICOLON):
            node.expression = self.parse_expression()

        self.expect(TokenType.DELIMITER_SEMICOLON)

        return node

    def parse_expression_or_assignment(self) -> AssignmentNode | ExpressionStatementNode:
        """
        Parse expression or assignment statement.

        Grammar:
            assignment = lvalue "=" expression ";"
            expr_stmt = expression ";"
        """
        # Parse the left side (but not including assignment operator)
        # We need to check if this is an assignment before parsing as full expression
        # So we parse postfix expression first (doesn't include binary operators)
        expr = self.parse_postfix_expression()

        # Check if it's an assignment
        if self.match(TokenType.OP_ASSIGN):
            self.advance()
            value = self.parse_expression()
            self.expect(TokenType.DELIMITER_SEMICOLON)

            return AssignmentNode(
                target=expr,
                value=value,
                line=expr.line,
                column=expr.column
            )
        else:
            # Continue parsing as expression if there are more operators
            # (e.g., "func() + 1" after parsing "func()")
            token = self.peek()
            if token.value in PRECEDENCE or token.type in (TokenType.KEYWORD_AND, TokenType.KEYWORD_OR):
                # Continue parsing the full binary expression
                # We already parsed the left side, so continue from there
                left = expr
                while True:
                    op_token = self.peek()
                    # Use canonical form for keywords (И, ИЛИ), original value for operators
                    if op_token.type == TokenType.KEYWORD_AND:
                        operator = 'И'
                    elif op_token.type == TokenType.KEYWORD_OR:
                        operator = 'ИЛИ'
                    elif op_token.type.name.startswith('OP_'):
                        operator = op_token.value
                    else:
                        operator = None

                    if not operator or operator not in PRECEDENCE:
                        break

                    precedence = PRECEDENCE[operator]

                    # Consume operator
                    self.advance()

                    # Parse right side with higher precedence
                    right = self.parse_binary_expression(precedence + 1)

                    # Create binary op node
                    left = BinaryOpNode(
                        left=left,
                        operator=operator,
                        right=right,
                        line=op_token.line,
                        column=op_token.column
                    )

                expr = left

            # Just an expression statement
            self.expect(TokenType.DELIMITER_SEMICOLON)
            return ExpressionStatementNode(
                expression=expr,
                line=expr.line,
                column=expr.column
            )

    # ==================== Expression Parsing ====================

    def parse_expression(self) -> Expression:
        """Parse an expression with operator precedence."""
        return self.parse_binary_expression(0)

    def parse_binary_expression(self, min_precedence: int) -> Expression:
        """
        Parse binary expression using precedence climbing.

        Args:
            min_precedence: Minimum operator precedence to parse

        Returns:
            Expression node
        """
        # Parse left side (primary or unary)
        left = self.parse_unary_expression()

        while True:
            # Skip newlines - expressions can span multiple lines
            self.skip_newlines()

            # Check if current token is an operator
            op_token = self.peek()
            # Use canonical form for keywords (И, ИЛИ), original value for operators
            if op_token.type == TokenType.KEYWORD_AND:
                operator = 'И'
            elif op_token.type == TokenType.KEYWORD_OR:
                operator = 'ИЛИ'
            elif op_token.type.name.startswith('OP_'):
                operator = op_token.value
            else:
                operator = None

            if not operator or operator not in PRECEDENCE:
                break

            precedence = PRECEDENCE[operator]
            if precedence < min_precedence:
                break

            # Consume operator
            self.advance()
            self.skip_newlines()

            # Parse right side with higher precedence
            right = self.parse_binary_expression(precedence + 1)

            # Create binary op node
            left = BinaryOpNode(
                left=left,
                operator=operator,
                right=right,
                line=op_token.line,
                column=op_token.column
            )

        return left

    def parse_unary_expression(self) -> Expression:
        """
        Parse unary expression.

        Grammar:
            unary = ("НЕ" | "-") unary | postfix
        """
        # Unary NOT
        if self.match(TokenType.KEYWORD_NOT):
            token = self.advance()
            operand = self.parse_unary_expression()
            return UnaryOpNode(
                operator="НЕ",
                operand=operand,
                line=token.line,
                column=token.column
            )

        # Unary minus
        if self.match(TokenType.OP_MINUS):
            token = self.advance()
            operand = self.parse_unary_expression()
            return UnaryOpNode(
                operator="-",
                operand=operand,
                line=token.line,
                column=token.column
            )

        return self.parse_postfix_expression()

    def parse_postfix_expression(self) -> Expression:
        """
        Parse postfix expression (member access, calls, indexing).

        Grammar:
            postfix = primary ("." identifier | "(" args ")" | "[" expression "]")*
        """
        expr = self.parse_primary_expression()

        while True:
            # Member access
            if self.match(TokenType.DELIMITER_DOT):
                token = self.advance()
                member_token = self.expect(TokenType.IDENTIFIER)
                expr = MemberAccessNode(
                    object=expr,
                    member=member_token.value,
                    line=token.line,
                    column=token.column
                )

            # Function call
            elif self.match(TokenType.DELIMITER_LPAREN):
                token = self.advance()
                args = []

                if not self.match(TokenType.DELIMITER_RPAREN):
                    args = self.parse_arguments()

                self.expect(TokenType.DELIMITER_RPAREN)

                expr = CallNode(
                    function=expr,
                    arguments=args,
                    line=token.line,
                    column=token.column
                )

            # Index access
            elif self.match(TokenType.DELIMITER_LBRACKET):
                token = self.advance()
                index = self.parse_expression()
                self.expect(TokenType.DELIMITER_RBRACKET)

                expr = IndexAccessNode(
                    object=expr,
                    index=index,
                    line=token.line,
                    column=token.column
                )

            else:
                break

        return expr

    def parse_primary_expression(self) -> Expression:
        """
        Parse primary expression (literals, identifiers, grouped expressions, etc.).

        Grammar:
            primary = literal | identifier | "Новый" type_name "(" args ")" | "(" expression ")" | "?" "(" args ")"
        """
        token = self.peek()

        # Ternary operator ?(condition, true_value, false_value)
        if self.match(TokenType.OP_TERNARY):
            return self.parse_ternary_expression()

        # Parenthesized expression
        if self.match(TokenType.DELIMITER_LPAREN):
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.DELIMITER_RPAREN)
            return expr

        # String literal
        if self.match(TokenType.LITERAL_STRING):
            token = self.advance()
            return LiteralNode(
                value=token.value,
                literal_type="string",
                line=token.line,
                column=token.column
            )

        # Number literal
        if self.match(TokenType.LITERAL_NUMBER):
            token = self.advance()
            # Try to parse as int, fall back to float
            try:
                value = int(token.value)
            except ValueError:
                value = float(token.value)

            return LiteralNode(
                value=value,
                literal_type="number",
                line=token.line,
                column=token.column
            )

        # Date literal
        if self.match(TokenType.LITERAL_DATE):
            token = self.advance()
            return LiteralNode(
                value=token.value,
                literal_type="date",
                line=token.line,
                column=token.column
            )

        # Boolean literals
        if self.match(TokenType.KEYWORD_TRUE):
            token = self.advance()
            return LiteralNode(
                value=True,
                literal_type="boolean",
                line=token.line,
                column=token.column
            )

        if self.match(TokenType.KEYWORD_FALSE):
            token = self.advance()
            return LiteralNode(
                value=False,
                literal_type="boolean",
                line=token.line,
                column=token.column
            )

        # Undefined
        if self.match(TokenType.KEYWORD_UNDEFINED):
            token = self.advance()
            return LiteralNode(
                value=None,
                literal_type="undefined",
                line=token.line,
                column=token.column
            )

        # New object
        if self.match(TokenType.KEYWORD_NEW):
            return self.parse_new_expression()

        # Identifier
        if self.match(TokenType.IDENTIFIER):
            token = self.advance()
            return IdentifierNode(
                name=token.value,
                line=token.line,
                column=token.column
            )

        raise ParserError(f"Unexpected token in expression: {token.value}", token)

    def parse_ternary_expression(self) -> TernaryNode:
        """
        Parse ternary conditional expression.

        Grammar:
            ternary = "?" "(" expression "," expression "," expression ")"
        """
        token = self.expect(TokenType.OP_TERNARY)
        node = TernaryNode(line=token.line, column=token.column)

        self.expect(TokenType.DELIMITER_LPAREN)
        node.condition = self.parse_expression()
        self.expect(TokenType.DELIMITER_COMMA)
        self.skip_newlines()
        node.true_value = self.parse_expression()
        self.expect(TokenType.DELIMITER_COMMA)
        self.skip_newlines()
        node.false_value = self.parse_expression()
        self.expect(TokenType.DELIMITER_RPAREN)

        return node

    def parse_new_expression(self) -> NewNode:
        """
        Parse object creation expression.

        Grammar:
            new = "Новый" type_name ("(" args ")")?
        """
        token = self.expect(TokenType.KEYWORD_NEW)

        type_token = self.expect(TokenType.IDENTIFIER)
        node = NewNode(
            type_name=type_token.value,
            line=token.line,
            column=token.column
        )

        # Optional constructor arguments
        if self.match(TokenType.DELIMITER_LPAREN):
            self.advance()

            if not self.match(TokenType.DELIMITER_RPAREN):
                node.arguments = self.parse_arguments()

            self.expect(TokenType.DELIMITER_RPAREN)

        return node

    def parse_arguments(self) -> list[Expression]:
        """
        Parse function call arguments.

        Grammar:
            arguments = expression ("," expression)*
        """
        args = []

        # First argument
        args.append(self.parse_expression())

        # Additional arguments
        while self.match(TokenType.DELIMITER_COMMA):
            self.advance()
            self.skip_newlines()
            args.append(self.parse_expression())

        return args
