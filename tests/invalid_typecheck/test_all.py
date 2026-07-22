import pytest
import os
import glob
from ampliphi.utils import get_ast, typecheck_ast
from ampliphi.exceptions import AmpliphiCompilationError


def get_test_files():
    test_dir = os.path.dirname(__file__)
    return glob.glob(os.path.join(test_dir, "*.aphi"))

@pytest.mark.parametrize("filepath", get_test_files())
def test_failing_type_check(filepath):
    with open(filepath, "r") as f:
        source_code = f.read()
    
    ast = get_ast(source_code)
    with pytest.raises(AmpliphiCompilationError):
        typecheck_ast(source_code, ast)
