from __future__ import annotations
from ..ast_nodes import *
from ..ir import *
from .node_visitor import NodeVisitor

op_map = {
    BinaryOperationType.ADD: BinOp.ADD,
    BinaryOperationType.SUB: BinOp.SUB,
    BinaryOperationType.GT:  BinOp.GT,
    BinaryOperationType.LT:  BinOp.LT,
    BinaryOperationType.AND: BinOp.AND,
    BinaryOperationType.OR:  BinOp.OR,
    BinaryOperationType.EQ:  BinOp.EQ,
}

class IRLowerer(NodeVisitor[str | None]):
    _program: IRProgram
    _temp_counter: int
    _label_counter: int
    _procedures: dict[str, ProcedureNode]
    
    def __init__(self) -> None:
        self._program = IRProgram()
        self._temp_counter = 0
        self._label_counter = 0
        self._procedures: dict[str, ProcedureNode] = {}

    @property
    def program(self) -> IRProgram:
        return self._program

    def _fresh_temp(self) -> str:
        name = f"__t{self._temp_counter}"
        self._temp_counter += 1
        self._program.variables[name] = IRType.TEMPORARY
        return name

    def _fresh_label(self, hint: str = "L") -> str:
        name = f"__{hint}_{self._label_counter}"
        self._label_counter += 1
        return name
    
    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode) -> None:
        name = node.identifier.contents
        ir_type = IRType.INT if node.variable_type == VariableType.INT else IRType.BOOL
        self._program.variables[name] = ir_type

    def visit_ArrayDeclarationNode(self, node: ArrayDeclarationNode) -> None:
        name = node.identifier.contents
        ir_type = IRType.INT_ARRAY if node.element_type == VariableType.INT else IRType.BOOL_ARRAY
        self._program.variables[name] = ir_type
        self._program.arrays[name] = node.size
    
    def visit_ProcedureNode(self, node: ProcedureNode) -> None:
        # Collect the name for inlining
        self._procedures[node.name.contents] = node

    def _emit_procedure_body(self, proc: ProcedureNode) -> None:
        for stmt in proc.statements:
            self.visit(stmt)

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        # We are starting to compile a new program; reset the state
        self._program = IRProgram()
        self._temp_counter = 0
        self._label_counter = 0
        self._procedures: dict[str, ProcedureNode] = {}

        # Visit every declaration
        for declaration in node.declarations:
            self.visit(declaration)

        # Visit every procedure
        for procedure in node.procedures:
            self.visit(procedure)

        # Emit main procedure only (guaranteed to exist by the typechecker)
        self._emit_procedure_body(self._procedures["main"])
        self._program.add(IRHalt())

    def visit_AssignmentStatementNode(self, node: AssignmentStatementNode) -> None:
        rhs = self.visit(node.expression)
        if isinstance(node.target, IdentifierNode):
            lhs = node.target.contents
            if lhs == rhs:
                # Skip assigning x = x altogether
                return
            else:
                self._program.add(IRCopy(dest=lhs, src=rhs))
        elif isinstance(node.target, ArrayAccessNode):
            array_name = node.target.array_name.contents
            index = self.visit(node.target.index)
            self._program.add(IRArrayStore(array_name=array_name, index=index, value=rhs))
    
    def visit_ArrayAccessNode(self, node: ArrayAccessNode) -> str:
        array_name = node.array_name.contents
        index = self.visit(node.index)
        
        # Determine element type
        array_type = self._program.variables[array_name]
        
        dest = self._fresh_temp()
        self._program.add(IRArrayLoad(dest=dest, array_name=array_name, index=index))
        return dest
    
    def visit_IfStatementNode(self, node: IfStatementNode) -> None:
        else_label = self._fresh_label("else")
        endif_label = self._fresh_label("endif")
        cond = node.condition.contents
        then_block = node.then_block
        else_block= node.else_block

        # Add the jump-if-cond-false first to avoid executing then-block
        self._program.add(IRJumpIfFalse(cond=cond, target=else_label))

        # Emit all instructions in the then-block
        for statement in then_block:
            self.visit(statement)

        # After then-block, jump to the endif to avoid executing the else-block
        self._program.add(IRJump(target=endif_label))
        
        # Emit all instructions in the else-block
        self._program.add(IRLabel(name=else_label))  
        for statement in else_block:
            self.visit(statement)
        
        # Add the endif label
        self._program.add(IRLabel(name=endif_label))  

    def visit_WhileStatementNode(self, node: WhileStatementNode) -> None:
        loop_label = self._fresh_label("while")
        end_label = self._fresh_label("endwhile")

        # Top of loop
        self._program.add(IRLabel(name=loop_label))
        cond_var = node.condition.contents

        # The jump-if-false comes first to skip the loop if the cond is false
        self._program.add(IRJumpIfFalse(cond=cond_var, target=end_label))

        for stmt in node.body:
            self.visit(stmt)
        
        # Go back to the top unconditionally
        self._program.add(IRJump(target=loop_label))

        # End of the loop
        self._program.add(IRLabel(name=end_label))


    def visit_InvokeStatementNode(self, node: InvokeStatementNode) -> None:
        # Inlining; the invoke sites are replaced by the IR of the procedure being invoked
        proc_name = node.procedure_name.contents
        proc = self._procedures[proc_name]
        self._emit_procedure_body(proc)


    def visit_BinaryOperationNode(self, node: BinaryOperationNode) -> str:
        """Return the name of the temporary variable assigned to the result of the binary operation."""
        left = self.visit(node.left)
        right = self.visit(node.right)
        ir_op = op_map[node.op]

        
        # Assign the result of the operation to a temp, and return the name of the temp
        dest = self._fresh_temp()
        self._program.add(IRBinOp(dest=dest, op=ir_op, left=left, right=right))
        return dest

    def visit_UnaryOperationNode(self, node: UnaryOperationNode) -> str:
        """Return the name of the temporary variable assigned to the result of the unary operation."""
        operand = self.visit(node.operand)
        ir_op = UnOp.NOT

        
        # Assign the result of the operation to a temp, and return the name of the temp
        dest = self._fresh_temp()
        self._program.add(IRUnOp(dest=dest, op=ir_op, operand=operand))
        return dest

    def visit_IdentifierNode(self, node: IdentifierNode) -> str:
        """Return the name of the identifier."""
        return node.contents

    def visit_IntegerLiteralNode(self, node: IntegerLiteralNode) -> str:
        """Return the name of the temporary variable assigned to the integer literal."""
        dest = self._fresh_temp()
        self._program.add(IRLoadInt(dest=dest, value=node.value))
        return dest

    def visit_BooleanLiteralNode(self, node: BooleanLiteralNode) -> str:
        """Return the name of the temporary variable assigned to the boolean literal."""
        dest = self._fresh_temp()
        self._program.add(IRLoadBool(dest=dest, value=node.value))
        return dest
