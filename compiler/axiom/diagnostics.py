from dataclasses import dataclass

from .ast import FunctionDef, Module


@dataclass(frozen=True, slots=True)
class Diagnostic:
    level: str
    code: str
    message: str


def check_module(module: Module) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not module.functions:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="module.empty",
                message=f"Module {module.name!r} has no functions.",
            )
        )

    for function in module.functions:
        diagnostics.extend(_check_function(function))

    return diagnostics


def _check_function(function: FunctionDef) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not function.purpose:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="function.missing_purpose",
                message=f"Function {function.name!r} has no purpose block.",
            )
        )

    if not function.action:
        diagnostics.append(
            Diagnostic(
                level="error",
                code="function.missing_action",
                message=f"Function {function.name!r} has no action block.",
            )
        )

    if not function.examples:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="function.missing_examples",
                message=f"Function {function.name!r} has no examples block.",
            )
        )

    return diagnostics
