from abc import ABC, abstractmethod
from ..ir import IRProgram

class IRPass(ABC):
    @abstractmethod
    def run(self, ir: IRProgram, **kwargs) -> IRProgram:
        pass