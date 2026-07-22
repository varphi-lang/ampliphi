from .ir_pass import IRPass
from ..ir import *
from .utils import *

class ConstantFoldingPass(IRPass):
    def run(self, program: IRProgram, **kwargs) -> IRProgram:
        # We need to know where labels are so we can jump to them during our simulation
        label_map = {instr.name: i for i, instr in enumerate(program.instructions) if isinstance(instr, IRLabel)}
        
        # in_states[i] tells us what we know about the variables right before instruction 'i' executes.
        # A variable can be in one of two states (this is called a "Lattice" in compiler theory):
        # 1. A constant value (e.g., 5, True): We know exactly what this variable is.
        # 2. "BOTTOM": This variable is definitely NOT a constant (e.g., it's user input, or it changes in a loop).
        in_states: list[dict[str, int | bool | str]] = [{} for _ in program.instructions]
        
        # At the very start of the program, all variables are "BOTTOM" because they are user inputs and we can't know their values yet.
        if program.instructions:
            in_states[0] = {v: "BOTTOM" for v in program.variables}
            # Also initialize all array elements to BOTTOM
            for a, size in program.arrays.items():
                for idx in range(size):
                    in_states[0][f"{a}[{idx}]"] = "BOTTOM"
        
        # The worklist keeps track of which instructions we need to evaluate/reevaluate because their input state changed.
        worklist = [0] if program.instructions else []
        # We also keep track of which instructions are actually reachable. If an instruction is never added here, it's dead code
        reachable = {0} if program.instructions else set()
        
        while worklist:
            i = worklist.pop(0)
            instr = program.instructions[i]
            state = in_states[i].copy()  # By the time we're done, this will contain the state of variables after this instruction runs
            
            # Determine how this instruction alters the state
            match instr:
                case IRLoadInt(dest=d, value=v) | IRLoadBool(dest=d, value=v):
                    # We are explicitly loading a constant, so we know 'd' is exactly 'v'
                    state[d] = v
                case IRCopy(dest=d, src=s):
                    # 'd' becomes whatever 's' currently is (might be a constant, might be BOTTOM)
                    state[d] = state.get(s, "BOTTOM")
                case IRBinOp(dest=d, op=op, left=l, right=r):
                    lv = state.get(l, "BOTTOM")
                    rv = state.get(r, "BOTTOM")
                    # If both operands are known constants, we can calculate the result right now!
                    if lv != "BOTTOM" and rv != "BOTTOM":
                        state[d] = evaluate_binop(op, lv, rv)
                    else:
                        # Otherwise, the result is unknown (BOTTOM)
                        state[d] = "BOTTOM"
                case IRUnOp(dest=d, op=op, operand=o):
                    val = state.get(o, "BOTTOM")
                    if val != "BOTTOM":
                        state[d] = evaluate_unop(op, val)
                    else:
                        state[d] = "BOTTOM"
                case IRArrayLoad(dest=d, array_name=a, index=idx_var):
                    idx_val = state.get(idx_var, "BOTTOM")
                    if idx_val != "BOTTOM":
                        # We know the index, so we can load the specific known value
                        # Clamp the index to the last element
                        idx_val = min(int(idx_val), program.arrays[a])
                        state[d] = state.get(f"{a}[{idx_val}]", "BOTTOM")
                    else:
                        # Unknown index, so the loaded value is unknown
                        state[d] = "BOTTOM"
                case IRArrayStore(array_name=a, index=idx_var, value=v_var):
                    idx_val = state.get(idx_var, "BOTTOM")
                    v_val = state.get(v_var, "BOTTOM")
                    if idx_val != "BOTTOM":
                        # We know the index, so we can store at that index
                        # Clamp the index to the last element
                        idx_val = min(int(idx_val), program.arrays[a])
                        state[f"{a}[{idx_val}]"] = v_val
                    else:
                        # We don't know which index is written, so ALL index values become unknown (any of them could have been written)
                        for idx in range(program.arrays[a]):
                            state[f"{a}[{idx}]"] = "BOTTOM"
                # Other instructions don't change variable states

            # Get the successor instructions of the current one
            successors = get_successors(program, i, label_map)
            
            # We need to do some special handling for jump instructions
            if isinstance(instr, IRJumpIfFalse):
                cond_val = state.get(instr.cond, "BOTTOM")
                if cond_val is True:
                    # The condition is definitely true, so we'll definitely not jump 
                    # So we remove the jump target from the successors.
                    successors = [s for s in successors if s != label_map[instr.target]]
                elif cond_val is False:
                    # The condition is definitely false, so we'll will definitely jump.
                    # So the only successor is the jump target.
                    successors = [label_map[instr.target]]
            
            # Now we propagate the variable states after this insturction has executed into the successors
            for succ in successors:
                reachable.add(succ)  # Make note that the successor instruction is not dead code
                # When paths merge (e.g., at a label), we have to combine the states using the "meet" operation.
                new_in = self._meet(in_states[succ], state)
                # If the successor's IN state changed because of us, we need to re-evaluate it, 
                # so we add it back to the worklist.
                if new_in != in_states[succ]:
                    in_states[succ] = new_in
                    if succ not in worklist:
                        worklist.append(succ)
        
        # Now rewrite the program accordingly 
        new_instructions = []
        for i, instr in enumerate(program.instructions):
            # If our simulation never reached this instruction, it's dead code and we can completely remove it
            if i not in reachable:
                continue 
                
            state = in_states[i]  # State of the variables before this instruction executes
            
            match instr:
                case IRBinOp(dest=d, op=op, left=l, right=r):
                    lv = state.get(l, "BOTTOM")
                    rv = state.get(r, "BOTTOM")
                    # If we figured out both operands are constants, replace the operation with a simple load
                    if lv != "BOTTOM" and rv != "BOTTOM":
                        val = evaluate_binop(op, lv, rv)
                        if isinstance(val, bool):
                            new_instructions.append(IRLoadBool(dest=d, value=val))
                        else:
                            new_instructions.append(IRLoadInt(dest=d, value=val))
                    else:
                        new_instructions.append(instr)
                        
                case IRUnOp(dest=d, op=op, operand=o):
                    val = state.get(o, "BOTTOM")
                    if val != "BOTTOM":
                        val = evaluate_unop(op, val)
                        if isinstance(val, bool):
                            new_instructions.append(IRLoadBool(dest=d, value=val))
                        else:
                            new_instructions.append(IRLoadInt(dest=d, value=val))
                    else:
                        new_instructions.append(instr)
                        
                case IRCopy(dest=d, src=s):
                    val = state.get(s, "BOTTOM")
                    # If we are copying a variable that we know is a constant, just load the constant directly
                    if val != "BOTTOM":
                        if isinstance(val, bool):
                            new_instructions.append(IRLoadBool(dest=d, value=val))
                        else:
                            new_instructions.append(IRLoadInt(dest=d, value=val))
                    else:
                        new_instructions.append(instr)
                        
                case IRArrayLoad(dest=d, array_name=a, index=idx_var):
                    idx_val = state.get(idx_var, "BOTTOM")
                    if idx_val != "BOTTOM" and 0 <= int(idx_val) < program.arrays[a]:
                        val = state.get(f"{a}[{idx_val}]", "BOTTOM")
                        if val != "BOTTOM":
                            # We know exactly what is in the array at this index, so just create a simple load
                            if isinstance(val, bool):
                                new_instructions.append(IRLoadBool(dest=d, value=val))
                            else:
                                new_instructions.append(IRLoadInt(dest=d, value=val))
                            continue
                    new_instructions.append(instr)
                        
                case IRJumpIfFalse(cond=c, target=t):
                    val = state.get(c, "BOTTOM")
                    if val is True:
                        # Condition is always true, so we never jump and we can just delete this jump entirely
                        pass
                    elif val is False:
                        # Condition is always false, so we always jump and can just replace this with an unconditional jump
                        new_instructions.append(IRJump(target=t))
                    else:
                        new_instructions.append(instr)
                        
                case _:
                    new_instructions.append(instr)

        return IRProgram(program.variables, program.arrays, new_instructions)

    def _meet(self, state1: dict, state2: dict) -> dict:
        """
        Rules:
        - If a variable is a constant on one path, but a different constant on the other path, it becomes BOTTOM.
        - If a variable is BOTTOM on any path, it becomes BOTTOM.
        - If a variable is the same constant on both paths, it stays that constant.
        """
        result = state1.copy()
        for k, v2 in state2.items():
            if k not in result:
                result[k] = v2
            else:
                v1 = result[k]
                if v1 == "BOTTOM" or v2 == "BOTTOM":
                    result[k] = "BOTTOM"
                elif v1 != v2:
                    result[k] = "BOTTOM"
        return result
