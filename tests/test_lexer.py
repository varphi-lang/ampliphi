import pytest
from ampliphi.lexer import AmpliphiLexer
from ampliphi.exceptions import AmpliphiCompilationError
from ampliphi.ply.lex import LexToken

@pytest.fixture
def lexer() -> AmpliphiLexer:
    """Return a clean instance of the lexer."""
    return AmpliphiLexer()

def get_tokens(lexer: AmpliphiLexer, input_string: str):
    """Given a lexer and input string, return a list of (type, value) tuples via the lexer."""
    return [(t.type, t.value) for t in lexer.tokenize(input_string)]

def get_full_tokens(lexer: AmpliphiLexer, input_string: str) -> list[LexToken]:
    """Given a lexer and input string, return a list of tokens via the lexer."""
    return list(lexer.tokenize(input_string))

@pytest.mark.parametrize("keyword, expected_type", [
    ("int", "INT"),
    ("bool", "BOOL"),
    ("procedure", "PROCEDURE"),
    ("invoke", "INVOKE"),
    ("if", "IF"),
    ("else", "ELSE"),
    ("while", "WHILE"),
    ("true", "TRUE"),
    ("false", "FALSE"),
])
def test_keywords(lexer: AmpliphiLexer, keyword: str, expected_type: str) -> None:
    tokens = get_tokens(lexer, keyword)
    assert tokens == [(expected_type, keyword)]

@pytest.mark.parametrize("symbol, expected_type", [
    ("+", "PLUS"),
    ("-", "MINUS"),
    ("&&", "AND"),
    ("||", "OR"),
    ("!", "NOT"),
    ("==", "EQEQ"),
    (">", "GT"),
    ("<", "LT"),
    ("=", "ASSIGN"),
    (";", "SEMICOLON"),
    ("(", "LPAREN"),
    (")", "RPAREN"),
    ("{", "LBRACE"),
    ("}", "RBRACE"),
    ("[", "LBRACKET"),
    ("]", "RBRACKET"),
])
def test_symbols(lexer: AmpliphiLexer, symbol: str, expected_type: str) -> None:
    tokens = get_tokens(lexer, symbol)
    assert tokens == [(expected_type, symbol)]

def test_numbers(lexer: AmpliphiLexer) -> None:
    # Test zero
    assert get_tokens(lexer, "0") == [("NUMBER", 0)]
    # Test single-digit number
    assert get_tokens(lexer, "1") == [("NUMBER", 1)]
    # Test multiple-digit integer
    assert get_tokens(lexer, "123") == [("NUMBER", 123)]

def test_identifiers(lexer: AmpliphiLexer) -> None:
    # Test string-only identifier
    assert get_tokens(lexer, "variableName") == [("IDENTIFIER", "variableName")]
    # Test identifier with letters and then numbers
    assert get_tokens(lexer, "var123") == [("IDENTIFIER", "var123")]
    # Test single-letter identifier
    assert get_tokens(lexer, "x") == [("IDENTIFIER", "x")]
    # Test all-caps identifier
    assert get_tokens(lexer, "SOMEVAR") == [("IDENTIFIER", "SOMEVAR")]
    # "if" is a keyword, but "ifblah" should be an identifier
    assert get_tokens(lexer, "ifblah") == [("IDENTIFIER", "ifblah")]

def test_number_vs_identifier(lexer: AmpliphiLexer) -> None:
    """Test boundary between numbers and identifiers."""
    # "123abc" = NUMBER(123) + IDENTIFIER(abc)
    assert get_tokens(lexer, "123abc") == [("NUMBER", 123), ("IDENTIFIER", "abc")]

def test_operator_greediness(lexer: AmpliphiLexer) -> None:
    """Test that double char operators are matched over single char ones."""
    # "==" should be EQEQ, not ASSIGN ASSIGN
    assert get_tokens(lexer, "==") == [("EQEQ", "==")]
    # "===" should be EQEQ ASSIGN
    assert get_tokens(lexer, "===") == [("EQEQ", "=="), ("ASSIGN", "=")]
    # "== =" Should be EQEQ ASSIGN
    assert get_tokens(lexer, "== =") == [("EQEQ", "=="), ("ASSIGN", "=")]

def test_ignore_whitespace(lexer: AmpliphiLexer) -> None:
    code = "int    x =  5 ;"
    expected = [
        ("INT", "int"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("NUMBER", 5),
        ("SEMICOLON", ";")
    ]
    assert get_tokens(lexer, code) == expected

def test_newline_tracking(lexer: AmpliphiLexer) -> None:
    code = """x
    y
    z"""
    tokens = get_full_tokens(lexer, code)
    
    assert len(tokens) == 3
    assert tokens[0].value == "x"
    assert tokens[0].lineno == 1
    
    assert tokens[1].value == "y"
    assert tokens[1].lineno == 2
    
    assert tokens[2].value == "z"
    assert tokens[2].lineno == 3

def test_multiple_newlines(lexer: AmpliphiLexer) -> None:
    code = "x\n\n\ny"
    tokens = get_full_tokens(lexer, code)
    assert tokens[0].value == "x"
    assert tokens[0].lineno == 1
    assert tokens[1].value == "y"
    assert tokens[1].lineno == 4

def test_assignment(lexer: AmpliphiLexer) -> None:
    code = "bool isReady = true;"
    expected = [
        ("BOOL", "bool"),
        ("IDENTIFIER", "isReady"),
        ("ASSIGN", "="),
        ("TRUE", "true"),
        ("SEMICOLON", ";")
    ]
    assert get_tokens(lexer, code) == expected

def test_block_structure(lexer: AmpliphiLexer) -> None:
    code = "procedure main { x = 1; }"
    expected = [
        ("PROCEDURE", "procedure"),
        ("IDENTIFIER", "main"),
        ("LBRACE", "{"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("NUMBER", 1),
        ("SEMICOLON", ";"),
        ("RBRACE", "}")
    ]
    assert get_tokens(lexer, code) == expected

def test_illegal_character(lexer: AmpliphiLexer) -> None:
    """Test that an exception is thrown on illegal tokens."""
    with pytest.raises(AmpliphiCompilationError) as excinfo:
        list(lexer.tokenize("int $ x;"))
    assert "Illegal token '$" in str(excinfo.value)

def test_singlecomment(lexer: AmpliphiLexer) -> None:
    """Test that single comments are ignored"""
    code = "int x = 5; // set x to 5"
    expected = [
        ("INT", "int"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("NUMBER", 5),
        ("SEMICOLON", ";")
    ]
    assert get_tokens(lexer, code) == expected

    
def test_blockcomment(lexer: AmpliphiLexer) -> None:
    """Test that block comments are ignored"""
    code = "int x = 5; /* set x to 5 */"
    expected = [
        ("INT", "int"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("NUMBER", 5),
        ("SEMICOLON", ";")
    ]
    assert get_tokens(lexer, code) == expected

def test_blockcomment_multiple_lines(lexer: AmpliphiLexer) -> None:
    """Test that block comments are ignored"""
    code = "int x = 5; /* set x \n to 5 */ \n int y = 4;"
    expected = [
        ("INT", "int"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("NUMBER", 5),
        ("SEMICOLON", ";"),
        ("INT", "int"),
        ("IDENTIFIER", "y"),
        ("ASSIGN", "="),
        ("NUMBER", 4),
        ("SEMICOLON", ";")
    ]
    assert get_tokens(lexer, code) == expected
    tokens = get_full_tokens(lexer, code)
    assert tokens[0].value == "int"
    assert tokens[0].lineno == 1
    assert tokens[6].value == "y"
    assert tokens[6].lineno == 3

def test_array_declaration_tokens(lexer: AmpliphiLexer) -> None:
    code = "int[3] A;"
    expected = [
        ("INT", "int"),
        ("LBRACKET", "["),
        ("NUMBER", 3),
        ("RBRACKET", "]"),
        ("IDENTIFIER", "A"),
        ("SEMICOLON", ";"),
    ]
    assert get_tokens(lexer, code) == expected

def test_array_access_tokens(lexer: AmpliphiLexer) -> None:
    code = "X = A[I];"
    expected = [
        ("IDENTIFIER", "X"),
        ("ASSIGN", "="),
        ("IDENTIFIER", "A"),
        ("LBRACKET", "["),
        ("IDENTIFIER", "I"),
        ("RBRACKET", "]"),
        ("SEMICOLON", ";"),
    ]
    assert get_tokens(lexer, code) == expected

def test_blockcomment_before_semicolon(lexer: AmpliphiLexer) -> None:
    """Test that block comments are ignored"""
    code = "int x = 5 /* set x to 5 */ ;"
    expected = [
        ("INT", "int"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("NUMBER", 5),
        ("SEMICOLON", ";")
    ]
    assert get_tokens(lexer, code) == expected   

