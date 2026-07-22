from dataclasses import dataclass
from .ast_nodes import ProgramNode, VariableType, VariableDeclarationNode, ArrayDeclarationNode
from .ir import IRProgram

@dataclass
class VariableInfo:
    name: str
    type: VariableType
    is_array: bool = False
    size: int = 1

def print_tokens(source_code: str) -> None:
    """Tokenize the source and print each token using a Rich table."""
    from rich.console import Console
    from rich.table import Table
    from .lexer import AmpliphiLexer

    lexer = AmpliphiLexer()
    console = Console()
    
    table = Table(title="Token Stream", show_header=True, header_style="bold magenta")
    
    table.add_column("Location", style="dim", width=12)
    table.add_column("Type", style="cyan")
    table.add_column("Value", style="green")

    for token in lexer.tokenize(source_code):
        col = lexer._find_column(token.lexpos)
        loc = f"{token.lineno}:{col}"
        table.add_row(loc, token.type, repr(token.value))

    console.print(table)

def get_ast(source_code: str) -> ProgramNode:
    from .parser import AmpliphiParser
    parser = AmpliphiParser()
    return parser.parse(source_code)

def typecheck_ast(source_code: str, tree: ProgramNode) -> None:
    from .visitors.type_check import TypeChecker
    type_checker = TypeChecker()
    type_checker.set_source_code(source_code)
    type_checker.visit(tree)

def print_ast_pretty(tree: ProgramNode) -> None:
    from .visitors.ast_printer import ASTPrinter
    printer = ASTPrinter()
    printer.visit(tree)

def print_ast_xml(tree: ProgramNode) -> None:
    from .visitors.xml_printer import XMLPrinter
    printer = XMLPrinter()
    printer.visit(tree)

def get_ir(tree: ProgramNode, optimize: bool = True) -> IRProgram:
    from .visitors.ir_lowering import IRLowerer
    from .opt import IRPass, ConstantFoldingPass, DeadCodeEliminationPass, TemporaryVariableReductionPass
    ir_lowering = IRLowerer()
    ir_lowering.visit(tree)
    program = ir_lowering.program
    if optimize:
        opt_passes: list[IRPass] = [
            ConstantFoldingPass(),
            TemporaryVariableReductionPass(),
            DeadCodeEliminationPass(),
        ]
        while True:
            old_program = program
            for opt_pass in opt_passes:
                program = opt_pass.run(program)
            if program == old_program:
                break
    return program

def get_varphi(ir: IRProgram) -> str:
    from .codegen import VarphiCodeGen
    return VarphiCodeGen(ir).generate()

def get_declarations(tree: ProgramNode) -> list[VariableInfo]:
    decls = []
    for decl in tree.declarations:
        if isinstance(decl, VariableDeclarationNode):
            decls.append(VariableInfo(name=decl.identifier.contents, type=decl.variable_type, is_array=False, size=1))
        elif isinstance(decl, ArrayDeclarationNode):
            decls.append(VariableInfo(name=decl.identifier.contents, type=decl.element_type, is_array=True, size=decl.size))
    return decls

def flatten_inputs(declarations: list[VariableInfo], inputs: dict) -> list[int]:
    tape_values = []
    for decl in declarations:
        if decl.name in inputs:
            vals = inputs[decl.name]
            if not isinstance(vals, list):
                vals = [vals]
            for v in vals:
                tape_values.append(int(v))
            # Pad if the provided list is shorter than size
            for _ in range(decl.size - len(vals)):
                tape_values.append(0)
        else:
            for _ in range(decl.size):
                tape_values.append(0)
    return tape_values

def unflatten_outputs(declarations: list[VariableInfo], tape_values: list[int]) -> dict:
    outputs = {}
    cursor = 0
    for decl in declarations:
        is_bool = (decl.type == VariableType.BOOL)
        if not decl.is_array:
            val = tape_values[cursor]
            outputs[decl.name] = bool(val >= 1) if is_bool else val
            cursor += 1
        else:
            vals = tape_values[cursor : cursor + decl.size]
            outputs[decl.name] = [bool(v >= 1) if is_bool else v for v in vals]
            cursor += decl.size
    return outputs

def run_program(source_code: str, inputs: dict, optimize: bool = True) -> dict:
    ast = get_ast(source_code)
    typecheck_ast(source_code, ast)
    declarations = get_declarations(ast)
    ir = get_ir(ast, optimize)
    varphi_code = get_varphi(ir)
    
    tape_values = flatten_inputs(declarations, inputs)
    output_tape = run_varphi_program(varphi_code, tape_values)
    return unflatten_outputs(declarations, output_tape)

def collect_variable_values(declarations: list[VariableInfo]) -> dict:
    from questionary import checkbox, text

    choices = []
    # Map raw decls to choices
    for decl in declarations:
        choices.append(decl.name)
            
    selected_choices = set(checkbox(
        "Select variables to initialize:",
        choices=choices
    ).ask())
    
    variable_values = {}
    for decl in declarations:
        if decl.name in selected_choices:
            if not decl.is_array:
                # Normal variable
                if decl.type == VariableType.INT:
                    val_str = text(
                        f"Value for {decl.name}:",
                        default="0",
                        validate=lambda t: t.strip().isdigit() or "Please enter a valid integer"
                    ).ask()
                    variable_values[decl.name] = int(val_str)
                else: # BOOL
                    val_str = text(
                        f"Value for {decl.name}:",
                        default="false",
                        validate=lambda t: t.strip().lower() in {"true", "false"} or "Please enter 'true' or 'false'"
                    ).ask()
                    variable_values[decl.name] = (val_str.strip().lower() == "true")
            else:
                # Array variable
                is_bool = (decl.type == VariableType.BOOL)
                
                def validate_array(text_input: str):
                    parts = [p.strip().lower() for p in text_input.split(",") if p.strip()]
                    if len(parts) != decl.size:
                        return f"Incorrect number of values! Size is {decl.size}."
                    
                    for p in parts:
                        if is_bool:
                            if p not in ["true", "false"]:
                                return f"Invalid boolean value: '{p}'. Use true/false."
                        else:
                            # Check for integer (including negative)
                            if not p.isdigit():
                                return f"Invalid integer value: '{p}'."
                    return True

                # Determine default and prompt
                default_val = ",".join(["false" if is_bool else "0"] * decl.size)
                prompt_msg = f"Values for {decl.name} ({'bool' if is_bool else 'int'} array[{decl.size}]):"

                val_str = text(
                    prompt_msg,
                    default=default_val,
                    validate=validate_array
                ).ask()
                
                # Parse the validated input
                raw_parts = [p.strip().lower() for p in val_str.split(",") if p.strip()]
                parts = []
                for p in raw_parts:
                    if is_bool:
                        parts.append(p == "true")
                    else:
                        parts.append(int(p))
                
                variable_values[decl.name] = parts

        else:
            if not decl.is_array:
                variable_values[decl.name] = False if decl.type == VariableType.BOOL else 0
            else:
                variable_values[decl.name] = [False if decl.type == VariableType.BOOL else 0] * decl.size
    return variable_values


def run_varphi_program(program: str, tape_values: list[int]) -> list[int]:
    from varphi_python import VarphiToPythonCompiler
    from contextlib import redirect_stdout, redirect_stderr
    import io
    import sys

    python_code = VarphiToPythonCompiler().compile(program)

    # Prepare the input
    lines = [str(len(tape_values))]
    for value in tape_values:
        lines.append('1' * value)
    lines.append("") # One empty line
    # Override stdin before execing
    old_stdin = sys.stdin
    sys.stdin = io.StringIO("\n".join(lines))

    new_stdout = io.StringIO()
    new_stderr = io.StringIO()
    with redirect_stdout(new_stdout), redirect_stderr(new_stderr):
        exec(python_code, {"__name__": "__main__"})
    sys.stdin = old_stdin

    # Now process the output
    output_lines = new_stdout.getvalue().splitlines()
    new_tape_values = []
    
    for i in range(len(tape_values)):
        # Output lines are 1-indexed for tapes
        line = output_lines[i + 1]
        new_tape_values.append(line.count('1'))
    return new_tape_values
