from typing import NoReturn
from .ply.yacc import yacc, YaccProduction

from .lexer import AmpliphiLexer
from .ast_nodes import *
from .exceptions import AmpliphiCompilationError

class AmpliphiParser:
    tokens = AmpliphiLexer.tokens
    start = 'program'

    _lexer_instance: AmpliphiLexer
    _parser: yacc
    _source_code: str

    def __init__(self) -> None:
        self._lexer_instance = AmpliphiLexer()
        self._parser = yacc(module=self)
        self._source_code = ""

    def _find_column(self, lexpos: int) -> int:
        """Calculates the column number from a 0-indexed lexpos."""
        end_of_last_line = self._source_code.rfind('\n', 0, lexpos)
        return lexpos - end_of_last_line

    def p_program(self, p: YaccProduction) -> None:
        """program : declarations procedures"""
        target_index = 1
        if not p[1] and len(p) > 2 and p[2]:
            target_index = 2

        p[0] = ProgramNode(
            lineno=p.lineno(target_index),
            colno=self._find_column(p.lexpos(target_index)),
            declarations=p[1],
            procedures=p[2]
        )
    
    def p_id(self, p: YaccProduction) -> None:
        """id : IDENTIFIER"""
        p[0] = IdentifierNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            contents=p[1]
        )

    def p_lists_extend(self, p: YaccProduction) -> None:
        """
        declarations : declarations declaration
        procedures   : procedures procedure
        statements   : statements statement
        """
        p[1].append(p[2])
        p[0] = p[1]

    def p_lists_empty(self, p: YaccProduction) -> None:
        """
        declarations : empty
        procedures   : empty
        statements   : empty
        """
        p[0] = []

    def p_declaration(self, p: YaccProduction) -> None:
        """declaration : type id SEMICOLON
                       | type LBRACKET NUMBER RBRACKET id SEMICOLON"""
        # If declaration is for integer or boolean
        if len(p) == 4:
            p[0] = VariableDeclarationNode(
                lineno=p.lineno(1),
                colno=self._find_column(p.lexpos(1)),
                variable_type=p[1],
                identifier=p[2]
            )
        # If declaration is for array
        else:
            p[0] = ArrayDeclarationNode(
                lineno=p.lineno(1),
                colno=self._find_column(p.lexpos(1)),
                element_type=p[1],
                size=int(p[3]),
                identifier=p[5]
            )

    def p_procedure(self, p: YaccProduction) -> None:
        """procedure : PROCEDURE id LBRACE statements RBRACE"""
        p[0] = ProcedureNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            name=p[2],
            statements=p[4]
        )

    def p_type(self, p: YaccProduction) -> None:
        """type : INT
                | BOOL"""
        p[0] = VariableType(p[1])

    def p_statement(self, p: YaccProduction) -> None:
        """statement : assignment
                     | if_statement
                     | while_statement
                     | invoke_statement"""
        p[0] = p[1]

    def p_assignment(self, p: YaccProduction) -> None:
        """assignment : id ASSIGN rhs SEMICOLON
                      | array_access ASSIGN rhs SEMICOLON"""
        p[0] = AssignmentStatementNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            target=p[1],
            expression=p[3]
        )

    def p_if_statement(self, p: YaccProduction) -> None:
        """if_statement : IF LPAREN id RPAREN LBRACE statements RBRACE ELSE LBRACE statements RBRACE"""
        p[0] = IfStatementNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            condition=p[3],
            then_block=p[6],
            else_block=p[10]
        )

    def p_while_statement(self, p: YaccProduction) -> None:
        """while_statement : WHILE LPAREN id RPAREN LBRACE statements RBRACE"""
        p[0] = WhileStatementNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            condition=p[3],
            body=p[6]
        )

    def p_invoke_statement(self, p: YaccProduction) -> None:
        """invoke_statement : INVOKE id SEMICOLON"""
        p[0] = InvokeStatementNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            procedure_name=p[2]
        )

    def p_rhs_operand(self, p: YaccProduction) -> None:
        """rhs : operand"""
        p[0] = p[1]

    def p_rhs_unary(self, p: YaccProduction) -> None:
        """rhs : unary_op operand"""
        p[0] = UnaryOperationNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            op=p[1],
            operand=p[2]
        )

    def p_rhs_binary(self, p: YaccProduction) -> None:
        """rhs : operand binary_op operand"""
        p[0] = BinaryOperationNode(
            lineno=p.lineno(2),
            colno=self._find_column(p.lexpos(2)),
            left=p[1],
            op=p[2],
            right=p[3]
        )

    def p_operand(self, p: YaccProduction) -> None:
        """operand : id
                   | int_literal
                   | bool_literal
                   | array_access"""
        p[0] = p[1]

    def p_array_access(self, p: YaccProduction) -> None:
        """array_access : id LBRACKET operand RBRACKET"""
        p[0] = ArrayAccessNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            array_name=p[1],
            index=p[3]
        )

    def p_binary_op(self, p: YaccProduction) -> None:
        """binary_op : PLUS
                     | MINUS
                     | GT
                     | LT
                     | EQEQ
                     | AND
                     | OR"""
        p[0] = BinaryOperationType(p[1])

    def p_unary_op(self, p: YaccProduction) -> None:
        """unary_op : NOT"""
        p[0] = UnaryOperationType(p[1])

    def p_bool_literal(self, p: YaccProduction) -> None:
        """bool_literal : TRUE
                        | FALSE"""
        p[0] = BooleanLiteralNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            value=(p[1] == "true")
        )

    def p_int_literal(self, p: YaccProduction) -> None:
        """int_literal : NUMBER"""
        p[0] = IntegerLiteralNode(
            lineno=p.lineno(1),
            colno=self._find_column(p.lexpos(1)),
            value=p[1]
        )

    def p_empty(self, _) -> None:
        """empty :"""
        pass

    def p_error(self, p: YaccProduction) -> NoReturn:
        if p:
            raise AmpliphiCompilationError(
                message=f"Syntax error at token {p.type} ('{p.value}')",
                lineno=p.lineno,
                column=self._find_column(p.lexpos),
                source_code=self._source_code
            )
        else:
            lines = self._source_code.splitlines()
            lineno = len(lines)
            raise AmpliphiCompilationError(
                message="Syntax error at EOF (Unexpected end of file)",
                lineno=lineno,
                column=len(lines[-1]) + 1 if lines else 1,
                source_code=self._source_code
            )
        
    def set_source_code(self, code: str) -> None:
        self._source_code = code

    def parse(self, program: str) -> ProgramNode:
        self.set_source_code(program)
        self._lexer_instance.set_source_code(program)
        lex = self._lexer_instance.get_lexer()
        lex.lineno = 1
        lex.lexpos = 0
        return self._parser.parse(
            program, 
            lexer=self._lexer_instance.get_lexer(), 
            tracking=True  # Allow productions to inherit line/lexpos info
        )