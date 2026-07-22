from typing import Iterator, NoReturn
from .ply.lex import lex, LexToken
from .exceptions import AmpliphiCompilationError

class AmpliphiLexer:
    tokens: tuple[str, ...] = (
        "INT",
        "BOOL",
        "PROCEDURE",
        "INVOKE",
        "IF",
        "ELSE",
        "WHILE",
        "TRUE",
        "FALSE",
        "NUMBER",
        "PLUS",
        "MINUS",
        "AND",
        "OR",
        "NOT",
        "EQEQ",
        "GT",
        "LT",
        "ASSIGN",
        "SEMICOLON",
        "LPAREN",
        "RPAREN",
        "LBRACE",
        "RBRACE",
        "LBRACKET",
        "RBRACKET",
        "IDENTIFIER",
    )

    reserved: dict[str, str] = {
        "int": "INT",
        "bool": "BOOL",
        "procedure": "PROCEDURE",
        "invoke": "INVOKE",
        "if": "IF",
        "else": "ELSE",
        "while": "WHILE",
        "true": "TRUE",
        "false": "FALSE",
    }

    t_PLUS      = r"\+"
    t_MINUS     = r"-"
    t_AND       = r"&&"
    t_OR        = r"\|\|"
    t_NOT       = r"!"
    t_EQEQ      = r"=="
    t_GT        = r">"
    t_LT        = r"<"
    t_ASSIGN    = r"="
    t_SEMICOLON = r";"
    t_LPAREN    = r"\("
    t_RPAREN    = r"\)"
    t_LBRACE    = r"\{"
    t_RBRACE    = r"\}"
    t_LBRACKET  = r"\["
    t_RBRACKET  = r"\]"

    t_ignore    = " \t"

    _lexer: lex
    _source_code: str

    def __init__(self) -> None:
        self._lexer = lex(module=self)
        self._source_code = ""

    def get_lexer(self) -> lex:
        return self._lexer

    def t_IDENTIFIER(self, t: LexToken) -> LexToken:
        r"[a-zA-Z][a-zA-Z0-9]*"
        # Reserved reserved keywords' types
        t.type = self.reserved.get(t.value, "IDENTIFIER")
        return t

    def t_NUMBER(self, t: LexToken) -> LexToken:
        r"\d+"
        t.value = int(t.value)
        return t

    def t_newline(self, t: LexToken) -> None:
        r"\n+"
        t.lexer.lineno += len(t.value)
    
    def t_SINGLECOMMENT(self, t: LexToken) -> None:
        r"//.*"
        pass

    def t_BLOCKCOMMENT(self, t: LexToken) -> None:
        r"/\*(?s:.*?)\*/"
        # Ignore block-line comments
        t.lexer.lineno += t.value.count('\n')

    def _find_column(self, lexpos: int) -> int:
        """Calculates the column number from a 0-indexed lexpos."""
        end_of_last_line = self._source_code.rfind('\n', 0, lexpos)
        return lexpos - end_of_last_line

    def t_error(self, t: LexToken) -> NoReturn:
        raise AmpliphiCompilationError(
            message=f"Illegal token '{t.value[0]}'",
            lineno=t.lexer.lineno,
            column=self._find_column(t.lexpos),
            source_code=self._source_code
        )
    
    def set_source_code(self, code: str) -> None:
        self._source_code = code

    def tokenize(self, program: str) -> Iterator[LexToken]:
        self.set_source_code(program)
        self._lexer.input(program)
        self._lexer.lineno = 1
        self._source_code = program
        for token in self._lexer:
            yield token
