from dataclasses import dataclass

from .app import AppSpec
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


def check_app(app: AppSpec) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not app.purpose:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_purpose",
                message=f"App {app.name!r} has no purpose block.",
            )
        )

    if not app.action:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_action",
                message=f"App {app.name!r} has no action block.",
            )
        )

    if not app.examples:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_examples",
                message=f"App {app.name!r} has no examples block.",
            )
        )

    if app.deploy is not None and any(not _is_safe_credential_reference(value) for value in app.deploy.credentials):
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="deploy.credentials_in_source",
                message="Deploy credentials should be referenced from environment or secrets, not stored in .ax files.",
            )
        )

    return diagnostics


def _is_safe_credential_reference(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered == "env" or lowered.startswith("env:") or lowered.startswith("secret:")


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
