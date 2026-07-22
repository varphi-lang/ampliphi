from pathlib import Path
import typer


app = typer.Typer(
    name="ampliphi",
    help="The frontend CLI for anything Ampliphi-related!",
    add_completion=True,
)



@app.command()
def compile(
    input_file: Path = typer.Argument(
        ...,
        help="Path to the Ampliphi source file.",
        exists=True,
        readable=True,
        dir_okay=False,
    ),
    tokens: bool = typer.Option(
        False, "--tokens", "-t",
        help="Print the token stream from the lexer.",
    ),
    ast: bool = typer.Option(
        False, "--ast", "-a",
        help="Print the abstract syntax tree.",
    ),
    check: bool = typer.Option(
        False, "--check", "-c",
        help="Check syntax only (do not compile).",
    ),
    xml: bool = typer.Option(
        False, "--xml", "-x",
        help="Print the AST in XML format.",
    ),
    ir: bool = typer.Option(
        False, "--ir", "-i",
        help="Print the intermediate representation.",
    ),
    run: bool = typer.Option(
        False, "--run", "-r",
        help="Run the compiled program immediately.",
    ),
    no_optimize: bool = typer.Option(
        False, "--no-opt",
        help="Disable optimizations"
    )
) -> None:
    """Compile and run an Ampliphi source file."""

    source_code = input_file.read_text()

    # --tokens: print the lexer token stream and exit
    if tokens:
        from .utils import print_tokens
        print_tokens(source_code)
        return

    # Parse the source into an AST
    from .utils import get_ast
    tree = get_ast(source_code)

    # We need to validate if there are type check errors
    from .utils import typecheck_ast
    typecheck_ast(source_code, tree)

    # --check: Compilation is successful at this point, print OK
    if check:
        typer.secho(f"{input_file}: OK", fg=typer.colors.GREEN)
        return

    if ast:
        from .utils import print_ast_pretty
        print_ast_pretty(tree)
        return
    
    if xml:
        from .utils import print_ast_xml
        print_ast_xml(tree)
        return
    
    # At this point we definitely have to compile to IR
    from .utils import get_ir
    ir_program = get_ir(tree, not no_optimize)
    
    if ir:
        print(ir_program.dump())
        return
    
    # At this point we definitely have to compile to Varphi
    from .utils import get_varphi
    
    if not run:
        # Emit to stdout
        varphi_code = get_varphi(ir_program)
        print(varphi_code)
        return

    # Now process the output
    from .utils import get_declarations, collect_variable_values, run_program
    from .ast_nodes import VariableType
    declarations = get_declarations(tree)
    initial_variable_values = collect_variable_values(declarations)
    
    final_values = run_program(source_code, initial_variable_values, not no_optimize)
    
    # Map final values back to variables
    for decl in declarations:
        val = final_values[decl.name]
        is_bool = (decl.type == VariableType.BOOL)
        
        if not decl.is_array:
            # Single value
            if is_bool:
                display_val = "true" if val else "false"
            else:
                display_val = val
                
            print(f"{decl.name}: {display_val}")
        else:
            # Array
            if is_bool:
                # Convert True/False to 'true' and 'false' strings
                display_values = ["true" if v else "false" for v in val]
                print(f"{decl.name}: [{', '.join(display_values)}]")
            else:
                print(f"{decl.name}: {val}")

def main() -> None:
    app()

if __name__ == "__main__":
    main()
