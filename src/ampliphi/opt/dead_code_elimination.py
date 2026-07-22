from .ir_pass import IRPass
from ..ir import *
from .utils import *

class DeadCodeEliminationPass(IRPass):
#    _call = 0
    def run(self, program: IRProgram, **kwargs) -> IRProgram:
#        DeadCodeEliminationPass._call += 1
#        print(f"[DCE #{self._call}] vars={list(program.variables.keys())[:3]} before: {len(program.instructions)}")
        _, out_sets = compute_liveness(program)
        
        new_instructions = []
        active_variables = set()
        
        for i, instruction in enumerate(program.instructions):
            defined = get_defined_variable(instruction, program)
            if defined and defined not in out_sets[i]:
                continue
            new_instructions.append(instruction)
            active_variables.update(get_used_variables(instruction, program))
            if defined:
                active_variables.add(defined)

        new_variables = {}
        for variable in program.variables:
            if is_temp(variable, program):
                if variable in active_variables:
                    new_variables[variable] = program.variables[variable]
            else:
                new_variables[variable] = program.variables[variable]

#        print(f"[DCE #{self._call}] after: {len(new_instructions)}")
        return IRProgram(new_variables, program.arrays, new_instructions)