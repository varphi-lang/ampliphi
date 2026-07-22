import sys
from typing import TextIO
from xml.sax.saxutils import escape
from ..ast_nodes import *
from .node_visitor import NodeVisitor


class XMLPrinter(NodeVisitor[None]):
    """A visitor that serializes the AST to XML."""

    def __init__(self, output: TextIO = sys.stdout) -> None:
        self._indent_level = 0
        self._output = output

    def _write(self, text: str) -> None:
        self._output.write("  " * self._indent_level + text + "\n")

    def _open(self, tag: str, **attrs: str | int | bool) -> None:
        attr_str = "".join(
            f' {k}="{escape(str(v))}"' for k, v in attrs.items() if v is not None
        )
        self._write(f"<{tag}{attr_str}>")
        self._indent_level += 1

    def _close(self, tag: str) -> None:
        self._indent_level -= 1
        self._write(f"</{tag}>")

    def _leaf(self, tag: str, **attrs: str | int | bool) -> None:
        attr_str = "".join(
            f' {k}="{escape(str(v))}"' for k, v in attrs.items() if v is not None
        )
        self._write(f"<{tag}{attr_str} />")

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        self._write('<?xml version="1.0" encoding="UTF-8"?>')
        self._open("Program", line=node.lineno, col=node.colno)

        if node.declarations:
            self._open("Declarations")
            for decl in node.declarations:
                self.visit(decl)
            self._close("Declarations")

        if node.procedures:
            self._open("Procedures")
            for proc in node.procedures:
                self.visit(proc)
            self._close("Procedures")

        self._close("Program")

    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode) -> None:
        self._open(
            "VariableDeclaration",
            type=node.variable_type.value,
            line=node.lineno,
            col=node.colno,
        )
        self.visit(node.identifier)
        self._close("VariableDeclaration")

    def visit_ArrayDeclarationNode(self, node: ArrayDeclarationNode) -> None:
        self._open(
            "ArrayDeclaration",
            type=node.element_type.value,
            size=node.size,
            line=node.lineno,
            col=node.colno,
        )
        self.visit(node.identifier)
        self._close("ArrayDeclaration")

    def visit_ProcedureNode(self, node: ProcedureNode) -> None:
        self._open("Procedure", line=node.lineno, col=node.colno)
        self.visit(node.name)
        if node.statements:
            self._open("Body")
            for stmt in node.statements:
                self.visit(stmt)
            self._close("Body")
        self._close("Procedure")

    def visit_AssignmentStatementNode(self, node: AssignmentStatementNode) -> None:
        self._open("Assignment", line=node.lineno, col=node.colno)
        self._open("Target")
        if isinstance(node.target, IdentifierNode):
            self.visit(node.target)
        else:
            self.visit_ArrayAccessNode(node.target)
        self._close("Target")
        self._open("Expression")
        self.visit(node.expression)
        self._close("Expression")
        self._close("Assignment")

    def visit_ArrayAccessNode(self, node: ArrayAccessNode) -> None:
        self._open("ArrayAccess", line=node.lineno, col=node.colno)
        self.visit(node.array_name)
        self._open("Index")
        self.visit(node.index)
        self._close("Index")
        self._close("ArrayAccess")

    def visit_IfStatementNode(self, node: IfStatementNode) -> None:
        self._open("If", line=node.lineno, col=node.colno)

        self._open("Condition")
        self.visit(node.condition)
        self._close("Condition")

        self._open("Then")
        for stmt in node.then_block:
            self.visit(stmt)
        self._close("Then")

        self._open("Else")
        for stmt in node.else_block:
            self.visit(stmt)
        self._close("Else")

        self._close("If")

    def visit_WhileStatementNode(self, node: WhileStatementNode) -> None:
        self._open("While", line=node.lineno, col=node.colno)
        self._open("Condition")
        self.visit(node.condition)
        self._close("Condition")
        self._open("Body")
        for stmt in node.body:
            self.visit(stmt)
        self._close("Body")
        self._close("While")

    def visit_InvokeStatementNode(self, node: InvokeStatementNode) -> None:
        self._open("Invoke", line=node.lineno, col=node.colno)
        self.visit(node.procedure_name)
        self._close("Invoke")

    def visit_BinaryOperationNode(self, node: BinaryOperationNode) -> None:
        self._open("BinaryOp", op=node.op.value, line=node.lineno, col=node.colno)
        self.visit(node.left)
        self.visit(node.right)
        self._close("BinaryOp")

    def visit_UnaryOperationNode(self, node: UnaryOperationNode) -> None:
        self._open("UnaryOp", op=node.op.value, line=node.lineno, col=node.colno)
        self.visit(node.operand)
        self._close("UnaryOp")

    def visit_IdentifierNode(self, node: IdentifierNode) -> None:
        self._leaf("Identifier", name=node.contents, line=node.lineno, col=node.colno)

    def visit_IntegerLiteralNode(self, node: IntegerLiteralNode) -> None:
        self._leaf("IntegerLiteral", value=node.value, line=node.lineno, col=node.colno)

    def visit_BooleanLiteralNode(self, node: BooleanLiteralNode) -> None:
        self._leaf(
            "BooleanLiteral",
            value=str(node.value).lower(),
            line=node.lineno,
            col=node.colno,
        )