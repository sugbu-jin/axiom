import re
from pathlib import Path

from axiom.app import AppComponent, AppSpec
from axiom.ast import Module
from axiom.transpiler_python import transpile_module

from .base import AxiomGeneratorError, BuildContext, StackGenerator


ENTRYPOINT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$")


class PythonCliGenerator(StackGenerator):
    stack = "python-cli"

    def build(self, context: BuildContext, modules: list[Module], apps: list[AppSpec]) -> list[Path]:
        outputs: list[Path] = []

        for module in modules:
            output_path = context.build / f"{module.name}.py"
            output_path.write_text(transpile_module(module), encoding="utf-8")
            outputs.append(output_path)

        for index, app in enumerate(apps):
            module_name = _entry_module(context.entry) if index == 0 else _module_name_from_project(app.name)
            output_path = context.build / f"{module_name}.py"
            output_path.write_text(_app_python_code(app), encoding="utf-8")
            outputs.append(output_path)

        main_path = context.build / "__main__.py"
        main_path.write_text(_entrypoint_code(context.entry), encoding="utf-8")
        outputs.append(main_path)

        return outputs


def _app_python_code(app: AppSpec) -> str:
    lines = [
        f'"""Generated Axiom app: {app.name}."""',
        "",
        "",
        "def main():",
        f"    print({('Axiom app: ' + app.name)!r})",
    ]

    for purpose in app.purpose:
        lines.append(f"    print({('Purpose: ' + purpose)!r})")
    for requirement in app.requires:
        lines.append(f"    print({('Requirement: ' + requirement)!r})")
    for action in app.action:
        lines.append(f"    print({('Action: ' + action)!r})")

    for component in _iter_components(app):
        stack = component.stack or "not specified"
        lines.append(f"    print({(component.name.title() + ' stack: ' + stack)!r})")
        for description in component.descriptions:
            lines.append(f"    print({('  - ' + description)!r})")

    if app.deploy is not None:
        target = app.deploy.target or "not specified"
        lines.append(f"    print({('Deploy target: ' + target)!r})")
        if app.deploy.credentials:
            lines.append("    print('Deploy credentials: configured outside generated code')")

    lines.extend(["    return 0", ""])
    return "\n".join(lines)


def _entrypoint_code(entry: str) -> str:
    if not ENTRYPOINT_RE.fullmatch(entry):
        raise AxiomGeneratorError("Project entry must use module.function format")

    module_name, function_name = entry.rsplit(".", 1)
    return "\n".join(
        [
            f"from {module_name} import {function_name}",
            "",
            "",
            "if __name__ == '__main__':",
            f"    result = {function_name}()",
            "    raise SystemExit(result if isinstance(result, int) else 0)",
            "",
        ]
    )


def _entry_module(entry: str) -> str:
    return entry.rsplit(".", 1)[0]


def _module_name_from_project(name: str) -> str:
    return name.replace("-", "_")


def _iter_components(app: AppSpec) -> list[AppComponent]:
    return [component for component in [app.frontend, app.backend, app.database] if component is not None]
