from .ir_pass import IRPass
from ..ir import *
from .utils import *

class TemporaryVariableReductionPass(IRPass):
    def run(self, program: IRProgram, **kwargs) -> IRProgram:
        in_sets, out_sets = compute_liveness(program)
        interference_graph = create_interference_graph(in_sets, out_sets, program)
        
        # We want to color and rename only temporary variables
        temporaries = [v for v, t in program.variables.items() if t == IRType.TEMPORARY]
        
        # Filter the interference graph to only include temporaries
        temp_graph = {t: set() for t in temporaries}
        for t in temporaries:
            temp_graph[t] = {n for n in interference_graph[t] if n in temporaries}
            
        color_map = get_variable_to_color(temp_graph)
        
        def swap(variable_name: str) -> str:
            if variable_name in color_map:
                return f"__t{color_map[variable_name]}"
            return variable_name

        new_instructions = []
        for instruction in program.instructions:
            match instruction:
                case IRLoadInt(dest=d, value=v):
                    new_instructions.append(IRLoadInt(dest=swap(d), value=v))
                case IRLoadBool(dest=d, value=v):
                    new_instructions.append(IRLoadBool(dest=swap(d), value=v))
                case IRCopy(dest=d, src=s):
                    new_instructions.append(IRCopy(dest=swap(d), src=swap(s)))
                case IRBinOp(dest=d, op=o, left=l, right=r):
                    new_instructions.append(IRBinOp(dest=swap(d), op=o, left=swap(l), right=swap(r)))
                case IRUnOp(dest=d, op=o, operand=a):
                    new_instructions.append(IRUnOp(dest=swap(d), op=o, operand=swap(a)))
                case IRArrayLoad(dest=d, array_name=a, index=i):
                    new_instructions.append(IRArrayLoad(dest=swap(d), array_name=a, index=swap(i)))
                case IRArrayStore(array_name=a, index=i, value=v):
                    new_instructions.append(IRArrayStore(array_name=a, index=swap(i), value=swap(v)))
                case IRJumpIfFalse(cond=c, target=t):
                    new_instructions.append(IRJumpIfFalse(cond=swap(c), target=t))
                case _:
                    new_instructions.append(instruction) # Labels, Jumps, Halts stay the same
        
        new_variables = {}
        for variable_name, typ in program.variables.items():
            new_variables[swap(variable_name)] = typ
            
        return IRProgram(new_variables, program.arrays.copy(), new_instructions)
