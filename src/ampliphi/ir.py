from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto

class IRType(Enum):
    INT = auto()
    BOOL = auto()
    INT_ARRAY = auto()
    BOOL_ARRAY = auto()
    TEMPORARY = auto()

class BinOp(Enum):
    ADD = auto()
    SUB = auto()
    GT = auto()
    LT = auto()
    EQ = auto()
    AND = auto()
    OR = auto()

class UnOp(Enum):
    NOT = auto()

@dataclass(frozen=True, slots=True)
class IRInstr:
    pass

@dataclass(frozen=True, slots=True)
class IRLabel(IRInstr):
    name: str

@dataclass(frozen=True, slots=True)
class IRLoadInt(IRInstr):
    dest: str
    value: int

@dataclass(frozen=True, slots=True)
class IRLoadBool(IRInstr):
    dest: str
    value: bool

@dataclass(frozen=True, slots=True)
class IRCopy(IRInstr):
    dest: str
    src: str

@dataclass(frozen=True, slots=True)
class IRBinOp(IRInstr):
    dest: str
    op: BinOp
    left: str
    right: str

@dataclass(frozen=True, slots=True)
class IRUnOp(IRInstr):
    dest: str
    op: UnOp
    operand: str

@dataclass(frozen=True, slots=True)
class IRArrayLoad(IRInstr):
    dest: str
    array_name: str
    index: str

@dataclass(frozen=True, slots=True)
class IRArrayStore(IRInstr):
    array_name: str
    index: str
    value: str

@dataclass(frozen=True, slots=True)
class IRJump(IRInstr):
    target: str  # A label name

@dataclass(frozen=True, slots=True)
class IRJumpIfFalse(IRInstr):
    cond: str
    target: str

@dataclass(frozen=True, slots=True)
class IRHalt(IRInstr):
    pass

@dataclass
class IRProgram:
    variables: dict[str, IRType] = field(default_factory=dict)
    arrays: dict[str, int] = field(default_factory=dict)
    instructions: list[IRInstr] = field(default_factory=list)

    def add(self, instr: IRInstr) -> None:
        self.instructions.append(instr)

    def dump(self) -> str:
        lines: list[str] = []
        lines.append("=== IR Program ===")
        lines.append("Variables:")
        for name, typ in self.variables.items():
            lines.append(f"  {name}: {typ.name}")
        lines.append("Arrays:")
        for name, size in self.arrays.items():
            lines.append(f"  {name}: {self.variables[name].name}[{size}]")
        lines.append("")
        lines.append("Instructions:")
        for instr in self.instructions:
            match instr:
                case IRLabel(name=n):
                    lines.append(f"{n}:")
                case IRLoadInt(dest=d, value=v):
                    lines.append(f"  {d} = {v}")
                case IRLoadBool(dest=d, value=v):
                    lines.append(f"  {d} = {'true' if v else 'false'}")
                case IRCopy(dest=d, src=s):
                    lines.append(f"  {d} = {s}")
                case IRBinOp(dest=d, op=o, left=l, right=r):
                    lines.append(f"  {d} = {l} {o.name} {r}")
                case IRUnOp(dest=d, op=o, operand=a):
                    lines.append(f"  {d} = {o.name} {a}")
                case IRJump(target=t):
                    lines.append(f"  JUMP {t}")
                case IRJumpIfFalse(cond=c, target=t):
                    lines.append(f"  JUMPIF_FALSE {c} -> {t}")
                case IRArrayLoad(dest=d, array_name=a, index=i):
                    lines.append(f"  {d} = {a}[{i}]")
                case IRArrayStore(array_name=a, index=i, value=v):
                    lines.append(f"  {a}[{i}] = {v}")
                case IRHalt():
                    lines.append(f"  HALT")
        return "\n".join(lines)
