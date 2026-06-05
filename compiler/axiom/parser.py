import re
from pathlib import Path

from .ast import FunctionDef, Module, Parameter


IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
FUNCTION_RE = re.compile(
    rf"^function\s+(?P<name>{IDENTIFIER})\((?P<params>.*)\)\s*->\s*(?P<return>{IDENTIFIER})\s*:$"
)
MODULE_RE = re.compile(rf"^module\s+(?P<name>{IDENTIFIER})$")

VALID_BLOCKS = {"purpose", "requires", "ensures", "action", "examples"}


class AxiomSyntaxError(Exception):
    """Raised when source cannot be parsed as Axiom."""


def parse_parameters(raw: str) -> list[Parameter]:
    raw = raw.strip()
    if not raw:
        return []

    params: list[Parameter] = []
    seen_names: set[str] = set()

    for item in raw.split(","):
        if ":" not in item:
            raise AxiomSyntaxError(f"Invalid parameter syntax: {item.strip()}")

        name, type_name = (part.strip() for part in item.split(":", 1))
        if not name or not type_name:
            raise AxiomSyntaxError(f"Invalid parameter syntax: {item.strip()}")
        if not re.fullmatch(IDENTIFIER, name):
            raise AxiomSyntaxError(f"Invalid parameter name: {name}")
        if not re.fullmatch(IDENTIFIER, type_name):
            raise AxiomSyntaxError(f"Invalid parameter type: {type_name}")
        if name in seen_names:
            raise AxiomSyntaxError(f"Duplicate parameter name: {name}")

        seen_names.add(name)
        params.append(Parameter(name=name, type_name=type_name))

    return params


def parse_file(path: str | Path) -> Module:
    return parse_source(Path(path).read_text(encoding="utf-8"))


def parse_source(source: str) -> Module:
    module: Module | None = None
    current_function: FunctionDef | None = None
    current_block: str | None = None

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if not raw_line.startswith(" "):
            module_match = MODULE_RE.match(stripped)
            if module_match:
                module = Module(name=module_match.group("name"))
                current_function = None
                current_block = None
                continue

            function_match = FUNCTION_RE.match(stripped)
            if function_match:
                if module is None:
                    raise AxiomSyntaxError(f"Line {line_number}: function declared before module")

                current_function = FunctionDef(
                    name=function_match.group("name"),
                    parameters=parse_parameters(function_match.group("params")),
                    return_type=function_match.group("return"),
                )
                module.functions.append(current_function)
                current_block = None
                continue

            raise AxiomSyntaxError(f"Line {line_number}: unexpected top-level statement: {stripped}")

        if current_function is None:
            raise AxiomSyntaxError(f"Line {line_number}: indented block outside function")

        block_candidate = stripped.removesuffix(":")
        if stripped.endswith(":") and block_candidate in VALID_BLOCKS:
            current_block = block_candidate
            continue

        if current_block is None:
            raise AxiomSyntaxError(f"Line {line_number}: statement outside known block: {stripped}")

        getattr(current_function, current_block).append(stripped)

    if module is None:
        raise AxiomSyntaxError("Missing module declaration")

    return module
