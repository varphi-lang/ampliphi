import pytest
import json
from pathlib import Path

from ampliphi.utils import run_program

# Get the absolute path to the tests directory
TESTS_DIR = Path(__file__).parent

def gather_test_cases():
    """Scans the tests directory for subdirectories containing test.aphi and io.json."""
    test_cases = []
    
    # Iterate through all subdirectories in tests/
    for test_number, test_dir in enumerate(TESTS_DIR.iterdir(), start=1): 
        if not test_dir.is_dir():
            continue        
        aphi_file = test_dir / "test.aphi"
        io_file = test_dir / "io.json"

        if not (aphi_file.exists() and io_file.exists()):
            continue

        io_data = json.loads(io_file.read_text(encoding="utf-8", errors="ignore"))
        source_code = aphi_file.read_text(encoding="utf-8", errors="ignore")

        for test_case in io_data:
            inp = test_case.get("input", {})
            out = test_case.get("output", {})

            test_cases.append(
                pytest.param(source_code, inp, out, True, id=f"{test_dir.name}{test_number}_opt_on")
            )
            test_cases.append(
                pytest.param(source_code, inp, out, False, id=f"{test_dir.name}{test_number}_opt_off")
            )
            
    return test_cases

@pytest.mark.parametrize("source_code, inp, out, optimize", gather_test_cases())
def test_e2e_compilation(source_code: str, inp: dict, out: dict, optimize: bool):
    outputs = run_program(source_code, inp, optimize=optimize)
    for k, v in out.items():
        assert outputs[k] == v