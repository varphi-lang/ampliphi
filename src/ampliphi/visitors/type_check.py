from enum import Enum
from .node_visitor import NodeVisitor
from ..ast_nodes import *
from ..exceptions import AmpliphiCompilationError
from typing import Union

class AmpliphiTypes(str, Enum):
    INT = "int"
    BOOL = "bool"
    PROCEDURE = "procedure"
    INT_ARRAY = "int[]"
    BOOL_ARRAY = "bool[]"

class TypeChecker(NodeVisitor[Union[None, AmpliphiTypes]]):
    """A vistor for constructing a symbol table and verifying types."""
    _symbol_table: dict[str, AmpliphiTypes]
    _source_code: str

    def __init__(self) -> None:
        self._symbol_table = {}
        self._source_code = ""
    
    def set_source_code(self, code: str) -> None:
        self._source_code = code

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        if len(node.declarations) == 0:
            source_code_split = self._source_code.splitlines()
            raise AmpliphiCompilationError(
                message=f"At least one variable declaration is required.",
                lineno=len(source_code_split),
                column=len(source_code_split[-1]) - 1 if len(source_code_split) != 0 else 0,
                source_code=self._source_code
            )
        self._symbol_table = {}
        for declaration in node.declarations:
            self.visit(declaration)

        for procedure in node.procedures:
            self.visit_ProcedureNode(procedure)
            
        if "main" not in self._symbol_table:
            source_code_split = self._source_code.splitlines()
            raise AmpliphiCompilationError(
                message=f"Missing 'main' procedure",
                lineno=len(source_code_split),
                column=len(source_code_split[-1]) - 1 if len(source_code_split) != 0 else 0,
                source_code=self._source_code
            )


    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode) -> None:
        variable_name = node.identifier.contents
        if variable_name in self._symbol_table:
            raise AmpliphiCompilationError(
                message=f"Redefinition of identifier '{variable_name}'",
                lineno=node.lineno,
                column=node.colno,
                source_code=self._source_code
            )
        match node.variable_type:
            case VariableType.INT:
                variable_type = AmpliphiTypes.INT
            case VariableType.BOOL:
                variable_type = AmpliphiTypes.BOOL        
        self._symbol_table[variable_name] = variable_type

    def visit_ArrayDeclarationNode(self, node: ArrayDeclarationNode) -> None:
        variable_name = node.identifier.contents
        if variable_name in self._symbol_table:
            raise AmpliphiCompilationError(
                message=f"Redefinition of identifier '{variable_name}'",
                lineno=node.lineno,
                column=node.colno,
                source_code=self._source_code
            )
        if node.size < 1:
            raise AmpliphiCompilationError(
                message=f"Invalid (non-positive) array size {node.size}.",
                lineno=node.lineno,
                column=node.colno,
                source_code=self._source_code
            )
        match node.element_type:
            case VariableType.INT:
                self._symbol_table[variable_name] = AmpliphiTypes.INT_ARRAY
            case VariableType.BOOL:
                self._symbol_table[variable_name] = AmpliphiTypes.BOOL_ARRAY

    def visit_ArrayAccessNode(self, node: ArrayAccessNode) -> AmpliphiTypes:
        array_type = self.visit(node.array_name)
        if array_type not in (AmpliphiTypes.INT_ARRAY, AmpliphiTypes.BOOL_ARRAY):
            raise AmpliphiCompilationError(
                message=f"Cannot index into '{node.array_name.contents}' because it is of type '{array_type.value}', not an array",
                lineno=node.lineno,
                column=node.colno,
                source_code=self._source_code
            )
        
        index_type = self.visit(node.index)
        if index_type is not AmpliphiTypes.INT:
            raise AmpliphiCompilationError(
                message=f"Array index must be 'int', but got '{index_type.value}'",
                lineno=node.index.lineno,
                column=node.index.colno,
                source_code=self._source_code
            )
        
        if array_type is AmpliphiTypes.INT_ARRAY:
            return AmpliphiTypes.INT
        else:
            return AmpliphiTypes.BOOL

    def visit_ProcedureNode(self, node: ProcedureNode) -> None:
        procedure_name = node.name.contents
        if procedure_name in self._symbol_table:
            raise AmpliphiCompilationError(
                message=f"Redefinition of identifier '{procedure_name}'",
                lineno=node.lineno,
                column=node.colno,
                source_code=self._source_code
            )
        for statement in node.statements:
            self.visit(statement)
        self._symbol_table[procedure_name] = AmpliphiTypes.PROCEDURE

    def visit_AssignmentStatementNode(self, node: AssignmentStatementNode) -> None:
        target_type = self.visit(node.target)
        if target_type is AmpliphiTypes.PROCEDURE:
            raise AmpliphiCompilationError(
                    message=f"Cannot assign to '{node.target.contents}' because it is a procedure, not a variable",
                    lineno=node.lineno,
                    column=node.colno,
                    source_code=self._source_code
                )
        if isinstance(node.target, IdentifierNode) and target_type in (AmpliphiTypes.INT_ARRAY, AmpliphiTypes.BOOL_ARRAY):
            raise AmpliphiCompilationError(
                    message=f"Cannot assign directly to array '{node.target.contents}'; use indexing (e.g. {node.target.contents}[i] = ...)",
                    lineno=node.lineno,
                    column=node.colno,
                    source_code=self._source_code
                )
        rhs_type = self.visit(node.expression)
        if target_type is not rhs_type:
            raise AmpliphiCompilationError(
                    message=f"Cannot assign expression of type '{rhs_type.value}' to a value of type '{target_type.value}'",
                    lineno=node.lineno,
                    column=node.colno,
                    source_code=self._source_code
                )


    def visit_IfStatementNode(self, node: IfStatementNode) -> None:
        condition_type = self.visit(node.condition)
        if condition_type is not AmpliphiTypes.BOOL:
            raise AmpliphiCompilationError(
                    message=f"Condition of 'if' statement must be 'bool', but '{node.condition.contents}' has type '{condition_type.value}'",
                    lineno=node.condition.lineno,
                    column=node.condition.colno,
                    source_code=self._source_code
                )
        for statement in node.then_block:
            self.visit(statement)
        for statement in node.else_block:
            self.visit(statement)

    def visit_WhileStatementNode(self, node: WhileStatementNode) -> None:
        condition_type = self.visit(node.condition)
        if condition_type is not AmpliphiTypes.BOOL:
            raise AmpliphiCompilationError(
                    message=f"Condition of 'while' statement must be 'bool', but '{node.condition.contents}' has type '{condition_type.value}'",
                    lineno=node.condition.lineno,
                    column=node.condition.colno,
                    source_code=self._source_code
                )
        for statement in node.body:
            self.visit(statement)

    def visit_InvokeStatementNode(self, node: InvokeStatementNode) -> None:
        id_type = self.visit(node.procedure_name)
        if id_type is not AmpliphiTypes.PROCEDURE:
            raise AmpliphiCompilationError(
                    message=f"Cannot invoke '{node.procedure_name.contents}' because it is of type '{id_type.value}', not a procedure",
                    lineno=node.procedure_name.lineno,
                    column=node.procedure_name.colno,
                    source_code=self._source_code
                )

    def visit_BinaryOperationNode(self, node: BinaryOperationNode) -> AmpliphiTypes:
        operand1_node = node.left
        operand1_type = self.visit(operand1_node)
        operand2_node = node.right
        operand2_type = self.visit(operand2_node)
        boolean_operators = {BinaryOperationType.AND, BinaryOperationType.OR}
        arithmetic_operators = {BinaryOperationType.ADD, BinaryOperationType.SUB}
        comparison_operators = {BinaryOperationType.GT, BinaryOperationType.LT}
        if node.op in boolean_operators:
            if operand1_type is not AmpliphiTypes.BOOL:
                raise AmpliphiCompilationError(
                    message=f"Invalid operand for operator '{node.op.value}' (expected 'bool', got '{operand1_type.value}')",
                    lineno=operand1_node.lineno,
                    column=operand1_node.colno,
                    source_code=self._source_code
                )
            elif operand2_type is not AmpliphiTypes.BOOL:
                raise AmpliphiCompilationError(
                    message=f"Invalid operand for operator '{node.op.value}' (expected 'bool', got '{operand2_type.value}')",
                    lineno=operand2_node.lineno,
                    column=operand2_node.colno,
                    source_code=self._source_code
                )
            return AmpliphiTypes.BOOL
        if node.op in arithmetic_operators:
            if operand1_type is not AmpliphiTypes.INT:
                raise AmpliphiCompilationError(
                    message=f"Invalid operand for operator '{node.op.value}' (expected 'int', got '{operand1_type.value}')",
                    lineno=operand1_node.lineno,
                    column=operand1_node.colno,
                    source_code=self._source_code
                )
            elif operand2_type is not AmpliphiTypes.INT:
                raise AmpliphiCompilationError(
                    message=f"Invalid operand for operator '{node.op.value}' (expected 'int', got '{operand2_type.value}')",
                    lineno=operand2_node.lineno,
                    column=operand2_node.colno,
                    source_code=self._source_code
                )
            return AmpliphiTypes.INT
        if node.op in comparison_operators:
            if operand1_type is not AmpliphiTypes.INT:
                raise AmpliphiCompilationError(
                    message=f"Invalid operand for operator '{node.op.value}' (expected 'int', got '{operand1_type.value}')",
                    lineno=operand1_node.lineno,
                    column=operand1_node.colno,
                    source_code=self._source_code
                )
            elif operand2_type is not AmpliphiTypes.INT:
                raise AmpliphiCompilationError(
                    message=f"Invalid operand for operator '{node.op.value}' (expected 'int', got '{operand2_type.value}')",
                    lineno=operand2_node.lineno,
                    column=operand2_node.colno,
                    source_code=self._source_code
                )
            return AmpliphiTypes.BOOL
        if node.op is BinaryOperationType.EQ:
            if operand1_type is not operand2_type:
                raise AmpliphiCompilationError(
                    message=f"Mismatched operand types for operator '{node.op.value}' ('{operand1_type.value}' and '{operand2_type.value}')",
                    lineno=operand2_node.lineno,
                    column=operand2_node.colno,
                    source_code=self._source_code
                )
            return AmpliphiTypes.BOOL


    def visit_UnaryOperationNode(self, node: UnaryOperationNode) -> AmpliphiTypes:
        operand_node = node.operand
        operand_type = self.visit(operand_node)
        if operand_type is not AmpliphiTypes.BOOL:
            raise AmpliphiCompilationError(
                message=f"Invalid operand for operator '{node.op.value}' (expected 'bool', got '{operand_type.value}')",
                lineno=operand_node.lineno,
                column=operand_node.colno,
                source_code=self._source_code
            )
        return AmpliphiTypes.BOOL

    def visit_IdentifierNode(self, node: IdentifierNode) -> AmpliphiTypes:
        if node.contents not in self._symbol_table:
            raise AmpliphiCompilationError(
                message=f"Unknown identifier '{node.contents}'",
                lineno=node.lineno,
                column=node.colno,
                source_code=self._source_code
            )
        return self._symbol_table[node.contents]

    def visit_IntegerLiteralNode(self, node: IntegerLiteralNode) -> AmpliphiTypes:
        return AmpliphiTypes.INT

    def visit_BooleanLiteralNode(self, node: BooleanLiteralNode) -> AmpliphiTypes:
        return AmpliphiTypes.BOOL