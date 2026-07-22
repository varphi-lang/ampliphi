from abc import ABC
from enum import Enum
from dataclasses import dataclass
from typing import Sequence

class BinaryOperationType(str, Enum):
    ADD = "+"
    SUB = "-"
    GT = ">"
    LT = "<"
    EQ = "=="
    AND = "&&"
    OR = "||"

class UnaryOperationType(str, Enum):
    NOT = "!"

class VariableType(str, Enum):
    INT = "int"
    BOOL = "bool"

@dataclass(frozen=True, slots=True)
class ASTNode(ABC):
    """Base class for all AST nodes."""
    lineno: int
    colno: int

class ExpressionASTNode(ASTNode):
    pass

class StatementASTNode(ASTNode):
    pass

@dataclass(frozen=True, slots=True)
class IdentifierNode(ExpressionASTNode):
    contents: str

@dataclass(frozen=True, slots=True)
class BooleanLiteralNode(ExpressionASTNode):
    value: bool

@dataclass(frozen=True, slots=True)
class IntegerLiteralNode(ExpressionASTNode):
    value: int

@dataclass(frozen=True, slots=True)
class BinaryOperationNode(ExpressionASTNode):
    left: ExpressionASTNode
    op: BinaryOperationType 
    right: ExpressionASTNode

@dataclass(frozen=True, slots=True)
class UnaryOperationNode(ExpressionASTNode):
    op: UnaryOperationType
    operand: ExpressionASTNode

@dataclass(frozen=True, slots=True)
class VariableDeclarationNode(ASTNode):
    variable_type: VariableType
    identifier: IdentifierNode

@dataclass(frozen=True, slots=True)
class ArrayDeclarationNode(ASTNode):
    element_type: VariableType
    size: int
    identifier: IdentifierNode

@dataclass(frozen=True, slots=True)
class ArrayAccessNode(ExpressionASTNode):
    array_name: IdentifierNode
    index: ExpressionASTNode

@dataclass(frozen=True, slots=True)
class AssignmentStatementNode(StatementASTNode):
    target: IdentifierNode | ArrayAccessNode
    expression: ExpressionASTNode 

@dataclass(frozen=True, slots=True)
class InvokeStatementNode(StatementASTNode):
    procedure_name: IdentifierNode

@dataclass(frozen=True, slots=True)
class IfStatementNode(StatementASTNode):
    condition: IdentifierNode
    then_block: Sequence[StatementASTNode]
    else_block: Sequence[StatementASTNode]

@dataclass(frozen=True, slots=True)
class WhileStatementNode(StatementASTNode):
    condition: IdentifierNode
    body: Sequence[StatementASTNode]

@dataclass(frozen=True, slots=True)
class ProcedureNode(ASTNode):
    name: IdentifierNode
    statements: Sequence[StatementASTNode]

@dataclass(frozen=True, slots=True)
class ProgramNode(ASTNode):
    declarations: Sequence[VariableDeclarationNode | ArrayDeclarationNode]
    procedures: Sequence[ProcedureNode]