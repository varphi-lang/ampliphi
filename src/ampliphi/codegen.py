from __future__ import annotations
from .ir import *

class VarphiCodeGen:
    _ir: IRProgram
    _lines: list[str]  # The lines of the Varphi program
    _state_counter: int
    _var_to_tape: dict[str, int]
    _num_tapes: int
    _label_states: dict[str, str]
    def __init__(self, ir: IRProgram) -> None:
        self._ir = ir
        self._lines = []
        self._state_counter = 0
        self._var_to_tape = {}
        self._num_tapes = 0
        self._label_states = {}

    def _fresh(self, hint: str = "s") -> str:
        """Generate a fresh state and return its name."""
        name = f"_{hint}_{self._state_counter}"
        self._state_counter += 1
        return name

    def _emit(self, cur: str, nxt: str, specs: dict[int, tuple[str, str, str]]) -> None:
        """
        This is a core function that emits a Varphi transition going from state `cur` to state `nxt`.
        Recall that Varphi transitions have 5 parts: a source state, a read tuple, a destination state, a write tuple, and a direction tuple, where
            - The source state and read tuple act like an if-statement: "if you are on this state and see these characters on the tapes, then..."
            - The destination state is the state to transition to if the if-statement is true
            - The write tuple contains the characters to write to each tape if the if-statement is true
            - The direction tuple contains the directions to move each head in if the if-statement is true
        `specs` will a mapping of tape numbers to a tuple containing three things:
            - What character to put in the read tuple for that tape
            - What character to put in the write tuple for that tape
            - What direction to put in the direction tuple for that tape
        If a tape number is not in `specs`, it will be "don't care"d. That is, the same element that is read will be written back, and the head will STAY.
        """
        reads: list[str] = []
        writes: list[str] = []
        dirs: list[str] = []
        dc = 0  # For making "don't care" variable names unique
        for t in range(self._num_tapes):
            if t in specs:
                # We want a particular rule for this tape, since it's in specs
                r, w, d = specs[t]
                reads.append(r)
                writes.append(w)
                dirs.append(d)
            else:
                # Wildcard for untouched tapes
                v = f"$dc{dc}" # The "don't care" variable goes in the read and write tuple
                dc += 1
                reads.append(v)
                writes.append(v)
                dirs.append("STAY")  # Don't move the head
        
        r_str = "(" + ", ".join(reads) + ")"
        w_str = "(" + ", ".join(writes) + ")"
        d_str = "(" + ", ".join(dirs) + ")"
        self._lines.append(f"{cur} {r_str} {nxt} {w_str} {d_str}")
    
    def _emit_comment(self, comment: str) -> None:
        comment_lines = comment.splitlines()
        if len(comment_lines) == 1:
            self._lines.append(f"// {comment}")
        else:
            self._lines.append("/*")
            for line in comment_lines:
                self._lines.append(line)
            self._lines.append("*/")

    def _emit_rewind(self, tape: int, fr: str) -> str:
        """Emit a routine to rewind a tape to its home position."""
        # TODO: As an optimization, put a "H" at the beginning of every tape to mark the home position. 
        self._emit_comment(f"Now rewinding tape {tape + 1}")
        s1 = self._fresh(f"rewindOnce")  # Our procedure entry state
        s2 = self._fresh(f"rewind")  # Our procedure entry state
        s3 = self._fresh(f"rewindDone")
        # Hand off unconditionally from the from-state to our entry state
        self._emit(fr, s1, {})
        # Move left unconditionally once (even if the head is already at home); hand off to rewinder.
        # We do this since the previous procedure may have left the head at a blank to the right of the value
        # This is why we need a particular character to mark the home position, but this will do for now
        self._emit(s1, s2, {tape: ("$any", "$any", "LEFT")})
        # Keep moving left while 1
        self._emit(s2, s2, {tape: ("1", "1", "LEFT")})
        # When you see blank, move back one right (the home position)
        self._emit(s2, s3, {tape: ("BLANK", "BLANK", "RIGHT")})
        return s3

    def _emit_clear(self, tape: int, fr: str) -> str:
        """Erase all 1s on a tape. The head will naturally be at home (on an arbitrary blank)"""
        self._emit_comment(f"Now clearing tape {tape + 1}")
        s1 = self._fresh(f"clear")
        s2 = self._fresh(f"clearDone")
        # Hand off unconditionally from the from-state to our entry state
        self._emit(fr, s1, {})
        # Clear until you see a BLANK
        self._emit(s1, s1, {tape: ("1", "BLANK", "RIGHT")})
        self._emit(s1, s2, {tape: ("BLANK", "BLANK", "STAY")})
        return s2

    def _emit_copy_data(self, dst: int, src: int, fr: str) -> str:
        """
        Copy data from `src` to `dst`.
        NOTE: It is assumed that `dst` has been **cleared** before copying.
        That is, there is absolutely no effort to clear `dst` in this procedure.
        """
        if dst == src:
            # Noop here
            return fr
        self._emit_comment(f"Now copying tape {src} into tape {dst}")
        s1 = self._fresh(f"copy")
        s2 = self._fresh(f"copyDone")
        # Hand off unconditionally from the from-state to our entry state
        self._emit(fr, s1, {})
        # Copy as long as src is a 1, otherwise stop
        self._emit(s1, s1, {src: ("1", "1", "RIGHT"), dst: ("$any", "1", "RIGHT")})
        self._emit(s1, s2, {src: ("BLANK", "BLANK", "STAY"), dst: ("$any", "$any", "STAY")})
        return s2

    def _emit_load_int(self, dest: str, value: int, fr: str) -> str:
        """
        Emit a procedure to load an arbitrary integer into a variable's tape.
        This will clear the tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {value}")
        tape = self._var_to_tape[dest]
        # First clear the tape
        current_state = self._emit_clear(tape, fr)
        # Now write the value in unary
        # TODO (Sprint 3): Don't write naively each tally one-by-one
        for i in range(value):
            # We make a state for each tally we have to write
            next_state = self._fresh(f"writeTally")  # The names are guaranteed to be unique
            # The direction we move in for the current state is STAY if this is the last tally we write
            direction = "RIGHT" if i < value - 1 else "STAY"
            # In all cases, we see a blank on this tape (as we cleared it) and write a tally
            self._emit(current_state, next_state, {tape: ("BLANK", "1", direction)})
            current_state = next_state
        current_state = self._emit_rewind(tape, current_state)
        return current_state

    def _emit_load_bool(self, dest: str, value: bool, fr: str) -> str:
        """
        Emit a procedure to load an arbitrary boolean into a variable's tape.
        This will clear the tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {value}")
        tape = self._var_to_tape[dest]
        # First clear the tape
        current_state = self._emit_clear(tape, fr)
        # Now write the value in unary
        # False stays blank, 0 for false. Else, tally by 1
        if value == True:
            next_state = self._fresh(f"writeTrue")
            self._emit(current_state, next_state, {tape: ("BLANK", "1", "STAY")})
            current_state = next_state
        current_state = self._emit_rewind(tape, current_state)
        return current_state

    def _emit_copy_var(self, dest: str, src: str, fr: str) -> str:
        """
        Emit a procedure to copy a variable's value into another variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {src}")
        destination_tape = self._var_to_tape[dest]
        source_tape = self._var_to_tape[src]
        # Clear the destination tape
        current_state = self._emit_clear(destination_tape, fr)
        # Copy the source to the destination
        current_state = self._emit_copy_data(destination_tape, source_tape, current_state)
        # Rewind both tapes
        current_state = self._emit_rewind(source_tape, current_state)
        current_state = self._emit_rewind(destination_tape, current_state)
        return current_state

    def _emit_add(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute the sum of two variables and store the result
        in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {left} + {right}")
        destination_tape = self._var_to_tape[dest]
        left_tape = self._var_to_tape[left]
        right_tape = self._var_to_tape[right]
        # Clear the destination
        current_state = self._emit_clear(destination_tape, fr)
        # Copy the left to the destination
        current_state = self._emit_copy_data(destination_tape, left_tape, current_state)
        # Copy the right to the destination (which has not yet rewinded), effectively adding right's value
        current_state = self._emit_copy_data(destination_tape, right_tape, current_state)
        # Rewind all tapes
        current_state = self._emit_rewind(destination_tape, current_state)
        current_state = self._emit_rewind(left_tape, current_state)
        current_state = self._emit_rewind(right_tape, current_state)
        return current_state

    def _emit_sub(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute the difference of two variables and store the result
        in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {left} - {right}")
        dt = self._var_to_tape[dest]
        lt = self._var_to_tape[left]
        rt = self._var_to_tape[right]

        # Clear the destination
        s = self._emit_clear(dt, fr)

        # Copy the left to the destination
        s = self._emit_copy_data(dt, lt, s)

        # Rewind both tapes
        for tape in [lt, dt]:
            s = self._emit_rewind(tape, s)

        # Now move both the right and destination heads together
        # for every tally on the right, make the corresponding destination cell blank
        s_done = self._fresh("subDone")
        self._emit(s, s, {rt: ("1", "1", "RIGHT"), dt: ("$any", "BLANK", "RIGHT")})
        self._emit(s, s_done, {rt: ("BLANK", "BLANK", "LEFT"), dt: ("$any", "$any", "STAY")})
        
        # Rewind all tapes
        for tape in [rt, dt]:
            s_done = self._emit_rewind(tape, s_done)
        return s_done

    def _emit_eq(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute the equality predicate of two variables and store
        the result in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {left} == {right}")
        destination_tape = self._var_to_tape[dest]
        left_tape = self._var_to_tape[left]
        right_tape = self._var_to_tape[right]
        
        # Clear the destination tape
        s_loop = self._emit_clear(destination_tape, fr)
        s_done = self._fresh("eqDone")

        # Both right and left are 1; keep scanning
        self._emit(s_loop, s_loop, {left_tape: ("1", "1", "RIGHT"), right_tape: ("1", "1", "RIGHT")})
        
        # Both are blank; this is a match. Write a 1 to the destination tape
        self._emit(s_loop, s_done, {left_tape: ("BLANK", "BLANK", "STAY"), right_tape: ("BLANK", "BLANK", "STAY"), destination_tape: ("$any", "1", "STAY")})
        
        # Mismatch; Do not write anything to the destination (it's already blank)
        self._emit(s_loop, s_done, {left_tape: ("1", "1", "STAY"), right_tape: ("BLANK", "BLANK", "STAY")})
        self._emit(s_loop, s_done, {left_tape: ("BLANK", "BLANK", "STAY"), right_tape: ("1", "1", "STAY")})

        # Rewind all tapes
        current_state = self._emit_rewind(destination_tape, s_done)
        current_state = self._emit_rewind(left_tape, current_state)
        current_state = self._emit_rewind(right_tape, current_state)
        return current_state
        

    def _emit_gt(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute the greater-than predicate and store the boolean
        result in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {left} > {right}")
        destination_tape = self._var_to_tape[dest]
        left_tape = self._var_to_tape[left]
        right_tape = self._var_to_tape[right]

        # Clear the destination tape
        s_loop = self._emit_clear(destination_tape, fr)
        s_done = self._fresh("gtDone")

        # Both right and left are 1; keep scanning
        self._emit(s_loop, s_loop, {left_tape: ("1", "1", "RIGHT"), right_tape: ("1", "1", "RIGHT")})

        # Both are blank; equal value, gt fails. write BLANK to dest.
        self._emit(s_loop, s_done, {left_tape: ("BLANK", "BLANK", "STAY"), right_tape: ("BLANK", "BLANK", "STAY"), destination_tape: ("BLANK", "BLANK", "STAY")})
  
        # Right is greater than left, gt fails. write BLANK to dest.
        self._emit(s_loop, s_done, {left_tape: ("BLANK", "BLANK", "STAY"), right_tape: ("1", "1", "STAY"), destination_tape: ("BLANK", "BLANK", "STAY")})
  
        # Left is greater than right, gt succeeds. Write 1 to dest.
        self._emit(s_loop, s_done, {left_tape: ("1", "1", "STAY"), right_tape: ("BLANK", "BLANK", "STAY"), destination_tape: ("$any", "1", "STAY")})
  
        # Rewind all tapes
        current_state = self._emit_rewind(destination_tape, s_done)
        current_state = self._emit_rewind(left_tape, current_state)
        current_state = self._emit_rewind(right_tape, current_state)
        return current_state


    def _emit_lt(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute the less-than predicate and store the boolean
        result in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {left} < {right}")
        return self._emit_gt(dest, right, left, fr)

    def _emit_and(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute boolean conjunction and store the boolean
        result in the destination variable.
        """
        self._emit_comment(f"Now computing {dest} = {left} && {right}")
        dt = self._var_to_tape[dest]
        lt = self._var_to_tape[left]
        rt = self._var_to_tape[right]

        # Clear the destination
        s_clear = self._emit_clear(dt, fr)
        s_true = self._fresh("andt")
        s_false = self._fresh("andf")

        # If both are 1: true
        self._emit(s_clear, s_true, {lt: ("1", "1", "STAY"), rt: ("1", "1", "STAY")})
        
        # Otherwise, false
        self._emit(s_clear, s_false, {lt: ("1", "1", "STAY"), rt: ("BLANK", "BLANK", "STAY")})
        self._emit(s_clear, s_false, {lt: ("BLANK", "BLANK", "STAY"), rt: ("1", "1", "STAY")})
        self._emit(s_clear, s_false, {lt: ("BLANK", "BLANK", "STAY"), rt: ("BLANK", "BLANK", "STAY")})

        s_done = self._fresh("andDone")
        self._emit(s_true, s_done, {dt: ("BLANK", "1", "STAY")})
        self._emit(s_false, s_done, {})
        return s_done

    def _emit_or(self, dest: str, left: str, right: str, fr: str) -> str:
        """
        Emit a procedure to compute boolean disjunction and store the boolean
        result in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        self._emit_comment(f"Now computing {dest} = {left} || {right}")
        dt = self._var_to_tape[dest]
        lt = self._var_to_tape[left]
        rt = self._var_to_tape[right]

        # Clear the destination
        s_clear = self._emit_clear(dt, fr)
        s_true = self._fresh("ort")
        s_false = self._fresh("orf")

        # If at least one are true: true
        self._emit(s_clear, s_true, {lt: ("1", "1", "STAY"), rt: ("1", "1", "STAY")})
        self._emit(s_clear, s_true, {lt: ("1", "1", "STAY"), rt: ("BLANK", "BLANK", "STAY")})
        self._emit(s_clear, s_true, {lt: ("BLANK", "BLANK", "STAY"), rt: ("1", "1", "STAY")})
        
        # Otherwise, false
        self._emit(s_clear, s_false, {lt: ("BLANK", "BLANK", "STAY"), rt: ("BLANK", "BLANK", "STAY")})

        s_done = self._fresh("orDone")
        self._emit(s_true, s_done, {dt: ("BLANK", "1", "STAY")})
        self._emit(s_false, s_done, {})
        return s_done

    def _emit_not(self, dest: str, operand: str, fr: str) -> str:
        """
        Emit a procedure to compute boolean negation and store the boolean
        result in the destination variable.
        This will clear the destination variable's tape and write the value.
        """
        # Clear the destination and write 1 if operand is BLANK, else write BLANK
        self._emit_comment(f"Now computing {dest} = !{operand}")
        destination_tape = self._var_to_tape[dest]
        operand_tape = self._var_to_tape[operand]

        # Clear the destination tape
        s_check = self._emit_clear(destination_tape, fr)
        s_done = self._fresh("notDone")

        # Operand is BLANK, write 1 to desination
        self._emit(s_check, s_done, {operand_tape: ("BLANK", "BLANK", "STAY"), destination_tape: ("$any", "1", "STAY")})

        # Operand isnt BLANK, keep destination BLANK
        self._emit(s_check, s_done, {operand_tape: ("1", "1", "STAY"), destination_tape: ("BLANK", "BLANK", "STAY")})

        # Rewind all tapes
        current_state = self._emit_rewind(destination_tape, s_done)
        current_state = self._emit_rewind(operand_tape, current_state)
        return current_state
      


    def _emit_jump_if_false(self, cond: str, true_state: str, false_state: str, fr: str) -> None:
        """
        Emit transitions that branch based on boolean condition variable.
        """
        condition_tape = self._var_to_tape[cond]
        self._emit(fr, false_state, {condition_tape: ("BLANK", "BLANK", "STAY")})
        self._emit(fr, true_state, {condition_tape: ("1", "1", "STAY")})

    def generate(self) -> str:
        self._allocate_tapes()
        self._collect_labels()
        self._generate_instructions()
        return self._format_output()

    def _allocate_tapes(self) -> None:
        idx = 0
        self._var_to_tape = {}
        for name, typ in self._ir.variables.items():
            if typ in (IRType.INT, IRType.BOOL, IRType.TEMPORARY):
                self._var_to_tape[name] = idx
                idx += 1
            elif typ in (IRType.INT_ARRAY, IRType.BOOL_ARRAY):
                self._var_to_tape[name] = idx
                size = self._ir.arrays[name]
                idx += size
        self._num_tapes = idx
        # TODO: Maybe add a scratch tape for binary doubling during loadint (Sprint 3 thing)
        

    def _emit_array_load(self, dest: str, array_name: str, index: str, fr: str) -> str:
        """
        Emit a procedure to load an array element into a variable's tape.
        """
        self._emit_comment(f"Now computing {dest} = {array_name}[{index}]")
        dest_tape = self._var_to_tape[dest]
        array_base_tape = self._var_to_tape[array_name]  # The tape for array[0]
        index_tape = self._var_to_tape[index]  # The tape containing the index value
        size = self._ir.arrays[array_name]  # The number of elements in the array
        
        # Clear the destination tape
        current_state = self._emit_clear(dest_tape, fr)
        
        s_done = self._fresh("arrayLoadDone")
        # We construct a "check" state for every possible index value [0, size - 1].
        # In addition, we also add a single check state for all indexes above the maximum, which will clamp the access to the last element of the list
        check_states = [self._fresh(f"check_{i}") for i in range(size + 1)]
        
        # We check if the index is 0 at check_states[0], if not then move onto check_states[1] and check if the index is 1, and so on...
        # If the check state matches the index, then we know what tape to read from...
        self._emit(current_state, check_states[0], {})
        
        for i in range(size):
            # If we see a 1 in the index tape, the index is not i
            # Move onto check_states[i + 1] to check if the index is i + 1
            self._emit(check_states[i], check_states[i+1], {index_tape: ("1", "1", "RIGHT")})
            
            # If we see a BLANK in the index tape, the index is i
            # We move to the copy phase now
            s_copy = self._fresh(f"locatedIndex")
            self._emit(check_states[i], s_copy, {index_tape: ("BLANK", "BLANK", "STAY")})
            current_state = self._emit_rewind(index_tape, s_copy)  # Rewind the index tape early in case we have i = arr[i]
            src_tape = array_base_tape + i
            current_state = self._emit_copy_data(dest_tape, src_tape, current_state)
            current_state = self._emit_rewind(src_tape, current_state)
            current_state = self._emit_rewind(dest_tape, current_state)
            current_state = self._emit_rewind(index_tape, current_state)
            self._emit(current_state, s_done, {})
        
        # We also have to handle out of bounds
        # check_states[size] means that index >= size, and in this case the behavior is the smae as an access to array[size - 1]
        s_copy = self._fresh(f"locatedIndex")
        self._emit(check_states[size], s_copy, {})
        current_state = self._emit_rewind(index_tape, s_copy)  # Rewind the index tape early in case we have i = arr[i]
        src_tape = array_base_tape + size - 1
        current_state = self._emit_copy_data(dest_tape, src_tape, current_state)
        current_state = self._emit_rewind(src_tape, current_state)
        current_state = self._emit_rewind(dest_tape, current_state)
        current_state = self._emit_rewind(index_tape, current_state)
        self._emit(current_state, s_done, {})
        return s_done

    def _emit_array_store(self, array_name: str, index: str, value: str, fr: str) -> str:
        """
        Emit a procedure to store a value into an array element.
        """
        self._emit_comment(f"Now computing {array_name}[{index}] = {value}")
        src_tape = self._var_to_tape[value]
        array_base_tape = self._var_to_tape[array_name]  # The tape for array[0]
        index_tape = self._var_to_tape[index]  # The tape containing the index value
        size = self._ir.arrays[array_name]  # The number of elements in the array
        
        s_done = self._fresh("arrayStoreDone")
        # We construct a "check" state for every possible index value [0, size - 1].
        # In addition, we also add a single check state for all indexes above the maximum, which will clamp the access to the last element of the list
        check_states = [self._fresh(f"check_{i}") for i in range(size + 1)]
        
        # We check if the index is 0 at check_states[0], if not then move onto check_states[1] and check if the index is 1, and so on...
        # If the check state matches the index, then we know what tape to read from...
        self._emit(fr, check_states[0], {})
        
        for i in range(size):
            # If we see a 1 in the index tape, the index is not i
            # Move onto check_states[i + 1] to check if the index is i + 1
            self._emit(check_states[i], check_states[i+1], {index_tape: ("1", "1", "RIGHT")})
            
            # If we see a BLANK in the index tape, the index is i
            # We move to the copy phase now
            s_copy = self._fresh(f"locatedIndex")
            self._emit(check_states[i], s_copy, {index_tape: ("BLANK", "BLANK", "STAY")})
            current_state = self._emit_rewind(index_tape, s_copy)  # Rewind the index tape early in case we have arr[i] = i
            dest_tape = array_base_tape + i
            current_state = self._emit_clear(dest_tape, current_state)
            current_state = self._emit_copy_data(dest_tape, src_tape, current_state)
            current_state = self._emit_rewind(src_tape, current_state)
            current_state = self._emit_rewind(dest_tape, current_state)
            self._emit(current_state, s_done, {})
        
        # We also have to handle out of bounds
        # check_states[size] means that index >= size, and in this case the behavior is the smae as an access to array[size - 1]
        s_copy = self._fresh(f"locatedIndex")
        self._emit(check_states[size], s_copy, {})
        current_state = self._emit_rewind(index_tape, s_copy)
        dest_tape = array_base_tape + size - 1
        current_state = self._emit_clear(dest_tape, current_state)
        current_state = self._emit_copy_data(dest_tape, src_tape, current_state)
        current_state = self._emit_rewind(src_tape, current_state)
        current_state = self._emit_rewind(dest_tape, current_state)
        
        self._emit(current_state, s_done, {})
        return s_done
    
    def _collect_labels(self) -> None:
        # We collect the labels first to be able to resolve jump statements where the label is below
        for instr in self._ir.instructions:
            if isinstance(instr, IRLabel):
                self._label_states[instr.name] = self._fresh("label")

    def _generate_instructions(self) -> None:
        current_state = self._fresh("start")
        for instr in self._ir.instructions:
            match instr:
                case IRLabel(name=name):
                    lbl_state = self._label_states[name]
                    if current_state != lbl_state:
                        self._emit(current_state, lbl_state, {})  # Do nothing except change state
                    current_state = lbl_state
                case IRLoadInt(dest=d, value=v):
                    current_state = self._emit_load_int(d, v, current_state)
                case IRLoadBool(dest=d, value=v):
                    current_state = self._emit_load_bool(d, v, current_state)
                case IRCopy(dest=d, src=s):
                    current_state = self._emit_copy_var(d, s, current_state)
                case IRBinOp(dest=d, op=op, left=l, right=r):
                    match op:
                        case BinOp.ADD:
                            current_state = self._emit_add(d, l, r, current_state)
                        case BinOp.SUB:
                            current_state = self._emit_sub(d, l, r, current_state)
                        case BinOp.GT:
                            current_state = self._emit_gt(d, l, r, current_state)
                        case BinOp.LT:
                            current_state = self._emit_lt(d, l, r, current_state)
                        case BinOp.EQ:
                            current_state = self._emit_eq(d, l, r, current_state)
                        case BinOp.AND:
                            current_state = self._emit_and(d, l, r, current_state)
                        case BinOp.OR:
                            current_state = self._emit_or(d, l, r, current_state)
                case IRUnOp(dest=d, op=UnOp.NOT, operand=a):
                    current_state = self._emit_not(d, a, current_state)
                case IRJump(target=t):
                    target_state = self._label_states[t]
                    self._emit(current_state, target_state, {})
                    current_state = self._fresh("dead")  # Fully, all the code after this point is dead (unless there's another label)
                case IRJumpIfFalse(cond=c, target=t):
                    false_state = self._label_states[t]
                    true_state = self._fresh("continue")
                    self._emit_jump_if_false(c, true_state, false_state, current_state)
                    current_state = true_state
                case IRArrayLoad(dest=d, array_name=a, index=i):
                    current_state = self._emit_array_load(d, a, i, current_state)
                case IRArrayStore(array_name=a, index=i, value=v):
                    current_state = self._emit_array_store(a, i, v, current_state)
                case IRHalt():
                    halt_state = self._fresh("HALT")
                    self._emit(current_state, halt_state, {})
                    current_state = self._fresh("dead")  # Everything is dead after a halt, unless there's a label

    def _format_output(self) -> str:
        header = [
            f"// Generated by Ampliphi compiler",
            f"// Hello from H, K, and Y :)",
            f"// Number of tapes: {self._num_tapes}"
        ]
        # Print the variable-to-tape mapping
        for name, idx in self._var_to_tape.items():
            typ = self._ir.variables[name]
            if typ in (IRType.INT_ARRAY, IRType.BOOL_ARRAY):
                size = self._ir.arrays[name]
                header.append(f"//   Tape {idx + 1}-{idx + size}: {name} ({typ.name}[{size}])")
            else:
                header.append(f"//   Tape {idx + 1}: {name} ({typ.name})")
        return "\n".join(header + self._lines) + "\n"