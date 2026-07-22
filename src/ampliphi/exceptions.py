class AmpliphiCompilationError(Exception):
    message: str
    lineno: int
    column: int
    source_code: str
    def __init__(self, message: str, lineno: int, column: int, source_code: str) -> None:
        self.message = message
        self.lineno = lineno
        self.column = column
        self.source_code = source_code
        super().__init__(message)

    def __str__(self) -> str:
        lines = self.source_code.splitlines()
        # NOTE: lineno is 1-indexed
        if 0 <= self.lineno - 1 < len(lines):
            error_line = lines[self.lineno - 1]
            pointer = " " * (self.column - 1) + "^"
            
            return (
                f"\nError: {self.message}\n"
                f"  Line {self.lineno}:\n"
                f"    {error_line}\n"
                f"    {pointer}"
            )
        
        return f"{self.message} at line {self.lineno} (Source unavailable)"