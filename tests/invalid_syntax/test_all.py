import pytest
from pathlib import Path
from ampliphi.utils import get_ast
from ampliphi.exceptions import AmpliphiCompilationError

TESTS_DIR = Path(__file__).parent

def gather_test_cases():
    test_cases = []
    for aphi_file in TESTS_DIR.glob("*.aphi"):
        source_code = aphi_file.read_text(encoding="utf-8", errors="ignore")
        test_cases.append(pytest.param(source_code, id=aphi_file.stem))
    return test_cases

@pytest.mark.parametrize("source_code", gather_test_cases())
def test_failing_syntax(source_code: str):
    with pytest.raises(AmpliphiCompilationError):
        get_ast(source_code)
