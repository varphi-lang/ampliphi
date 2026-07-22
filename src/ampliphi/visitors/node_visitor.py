from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any
from ..ast_nodes import *

T = TypeVar("T")

class NodeVisitor(ABC, Generic[T]):
    """A generic Visitor base class."""

    def visit(self, to_visit: ASTNode | list[ASTNode]) -> T | list[T]:
        if isinstance(to_visit, list):
            return [self.visit(item) for item in to_visit]
        
        method_name = f"visit_{type(to_visit).__name__}"
        visitor = getattr(self, method_name)
        return visitor(to_visit)

    @abstractmethod
    def visit_ProgramNode(self, node: ProgramNode) -> T:
        pass

    @abstractmethod
    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode) -> T:
        pass

    @abstractmethod
    def visit_ArrayDeclarationNode(self, node: ArrayDeclarationNode) -> T:
        pass

    @abstractmethod
    def visit_ProcedureNode(self, node: ProcedureNode) -> T:
        pass

    @abstractmethod
    def visit_AssignmentStatementNode(self, node: AssignmentStatementNode) -> T:
        pass

    @abstractmethod
    def visit_IfStatementNode(self, node: IfStatementNode) -> T:
        pass

    @abstractmethod
    def visit_WhileStatementNode(self, node: WhileStatementNode) -> T:
        pass

    @abstractmethod
    def visit_InvokeStatementNode(self, node: InvokeStatementNode) -> T:
        pass

    @abstractmethod
    def visit_BinaryOperationNode(self, node: BinaryOperationNode) -> T:
        pass

    @abstractmethod
    def visit_UnaryOperationNode(self, node: UnaryOperationNode) -> T:
        pass

    @abstractmethod
    def visit_IdentifierNode(self, node: IdentifierNode) -> T:
        pass

    @abstractmethod
    def visit_IntegerLiteralNode(self, node: IntegerLiteralNode) -> T:
        pass

    @abstractmethod
    def visit_BooleanLiteralNode(self, node: BooleanLiteralNode) -> T:
        pass
        
    @abstractmethod
    def visit_ArrayAccessNode(self, node: ArrayAccessNode) -> T:
        pass