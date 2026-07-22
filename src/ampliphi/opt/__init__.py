from .temp_reduction import TemporaryVariableReductionPass
from .constant_folding import ConstantFoldingPass
from .dead_code_elimination import DeadCodeEliminationPass
from .ir_pass import IRPass

__all__ = [
    "TemporaryVariableReductionPass",
    "DeadCodeEliminationPass",
    "ConstantFoldingPass",
    "IRPass"
]