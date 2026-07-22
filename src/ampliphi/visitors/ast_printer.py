import sys
from typing import TextIO
from ..ast_nodes import *
from .node_visitor import NodeVisitor

class ASTPrinter(NodeVisitor[None]):
    """A visitor that prints the AST structure."""
    def __init__(self, output: TextIO = sys.stdout):
        self._indent_level = 0
        self._output = output

    def _log(self, msg: str) -> None:
        self._output.write("  " * self._indent_level + msg + "\n")

    def _print_block(self, header: str, nodes: list[StatementASTNode] | list[VariableDeclarationNode]) -> None:
        if not nodes:
            return
        self._log(f"{header}:")
        self._indent_level += 1
        for node in nodes:
            self.visit(node)
        self._indent_level -= 1

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        self._log("ProgramNode")
        self._indent_level += 1
        self._print_block("Declarations", node.declarations)
        self._print_block("Procedures", node.procedures)
        self._indent_level -= 1

    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode) -> None:
        self._log(f"VariableDeclaration: {node.variable_type.value} {node.identifier.contents}")

    def visit_ArrayDeclarationNode(self, node: ArrayDeclarationNode) -> None:
        self._log(f"ArrayDeclaration: {node.element_type.value}[{node.size}] {node.identifier.contents}")
    
    def visit_ProcedureNode(self, node: ProcedureNode) -> None:
        self._log(f"Procedure: {node.name.contents}")
        self._indent_level += 1
        self._print_block("Statements", node.statements)
        self._indent_level -= 1

    def visit_AssignmentStatementNode(self, node: AssignmentStatementNode) -> None:
        self._log(f"Assignment: ")
        self._indent_level += 1
        self._log("Target:")
        self._indent_level += 1
        self.visit(node.target)
        self._indent_level -= 1
        self._indent_level -= 1
    
    def visit_ArrayAccessNode(self, node: ArrayAccessNode) -> None:
        self._log(f"ArrayAccess: {node.array_name.contents}")
        self._indent_level += 1
        self._log("Index: ")
        self._indent_level += 1
        self.visit(node.index)
        self._indent_level -= 1
        self._indent_level -= 1
    
    def visit_IfStatementNode(self, node: IfStatementNode) -> None:
        self._log(f"If ({node.condition.contents})")
        self._indent_level += 1
        self._print_block("Then Block Statements", node.then_block)
        if node.else_block:
            self._print_block("Else Block Statements", node.else_block)
        self._indent_level -= 1

    def visit_WhileStatementNode(self, node: WhileStatementNode) -> None:
        self._log(f"While ({node.condition.contents})")
        self._indent_level += 1
        self._print_block("Body", node.body)
        self._indent_level -= 1

    def visit_InvokeStatementNode(self, node: InvokeStatementNode) -> None:
        self._log(f"Invoke: {node.procedure_name.contents}")

    def visit_BinaryOperationNode(self, node: BinaryOperationNode) -> None:
        self._log(f"BinaryOperation: {node.op.value}")
        self._indent_level += 1
        self.visit(node.left)
        self.visit(node.right)
        self._indent_level -= 1

    def visit_UnaryOperationNode(self, node: UnaryOperationNode) -> None:
        self._log(f"UnaryOperation: {node.op.value}")
        self._indent_level += 1
        self.visit(node.operand)
        self._indent_level -= 1

    def visit_IdentifierNode(self, node: IdentifierNode) -> None:
        self._log(f"Identifier: {node.contents}")

    def visit_IntegerLiteralNode(self, node: IntegerLiteralNode) -> None:
        self._log(f"IntegerLiteral: {node.value}")

    def visit_BooleanLiteralNode(self, node: BooleanLiteralNode) -> None:
        self._log(f"BooleanLiteral: {str(node.value).lower()}")