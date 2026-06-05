import re
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

from .app import AppComponent, AppSpec, DeploySpec
from .app_parser import is_app_source, parse_app_source
from .parser import parse_file
from .transpiler_python import transpile_module


PROJECT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
ENTRYPOINT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$")
CONFIG_FILE = "axiom.toml"
DEFAULT_STACK = "python-cli"
SUPPORTED_STACKS = {"python-cli", "static-site"}


class AxiomProjectError(Exception):
    """Raised when an Axiom project cannot be created, built, or run."""


@dataclass(frozen=True, slots=True)
class Project:
    root: Path
    name: str
    stack: str
    source: Path
    build: Path
    entry: str


def create_project(name: str, parent: str | Path = ".", stack: str = DEFAULT_STACK) -> Path:
    if not PROJECT_NAME_RE.fullmatch(name):
        raise AxiomProjectError(
            "Project name must start with a letter and contain only letters, numbers, hyphens, or underscores."
        )
    if stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    root = Path(parent) / name
    if root.exists() and any(root.iterdir()):
        raise AxiomProjectError(f"Directory already exists and is not empty: {root}")

    module_name = _module_name_from_project(name)
    source_dir = root / "src"
    source_dir.mkdir(parents=True, exist_ok=True)

    (root / CONFIG_FILE).write_text(
        "\n".join(
            [
                f'name = "{name}"',
                f'stack = "{stack}"',
                'source = "src"',
                'build = "build"',
                f'entry = "{module_name}.main"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (source_dir / "main.ax").write_text(_starter_source(module_name, stack), encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(name, stack), encoding="utf-8")

    return root


def load_project(path: str | Path = ".") -> Project:
    root = Path(path).resolve()
    config_path = root / CONFIG_FILE
    if not config_path.exists():
        raise AxiomProjectError(f"Missing {CONFIG_FILE} in {root}")

    config = _read_config(config_path)
    name = config.get("name", root.name)
    stack = config.get("stack", DEFAULT_STACK)
    if stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    source = root / config.get("source", "src")
    build = root / config.get("build", "build")
    entry = config.get("entry", f"{_module_name_from_project(name)}.main")

    return Project(root=root, name=name, stack=stack, source=source, build=build, entry=entry)


def build_project(path: str | Path = ".") -> list[Path]:
    project = load_project(path)
    if not project.source.exists():
        raise AxiomProjectError(f"Missing source directory: {project.source}")

    source_files = sorted(project.source.rglob("*.ax"))
    if not source_files:
        raise AxiomProjectError(f"No .ax source files found in {project.source}")

    project.build.mkdir(parents=True, exist_ok=True)
    apps: list[AppSpec] = []
    modules = []

    for source_file in source_files:
        source = source_file.read_text(encoding="utf-8")
        if is_app_source(source):
            apps.append(parse_app_source(source))
        else:
            modules.append(parse_file(source_file))

    if project.stack == "python-cli":
        return _build_python_cli(project, modules, apps)
    if project.stack == "static-site":
        return _build_static_site(project, modules, apps)

    raise AxiomProjectError(_unsupported_stack_message(project.stack))


def _build_python_cli(project: Project, modules: list, apps: list[AppSpec]) -> list[Path]:
    outputs: list[Path] = []

    for module in modules:
        output_path = project.build / f"{module.name}.py"
        output_path.write_text(transpile_module(module), encoding="utf-8")
        outputs.append(output_path)

    for index, app in enumerate(apps):
        module_name = _entry_module(project.entry) if index == 0 else _module_name_from_project(app.name)
        output_path = project.build / f"{module_name}.py"
        output_path.write_text(_app_python_code(app), encoding="utf-8")
        outputs.append(output_path)

    main_path = project.build / "__main__.py"
    main_path.write_text(_entrypoint_code(project.entry), encoding="utf-8")
    outputs.append(main_path)

    return outputs


def run_project(path: str | Path = ".") -> int:
    project = load_project(path)
    build_project(project.root)

    if project.stack == "static-site":
        index_path = project.build / "index.html"
        print(f"Static site built at {index_path}")
        return 0

    result = subprocess.run([sys.executable, "__main__.py"], cwd=project.build, text=True)
    return result.returncode


def list_stacks() -> list[str]:
    return sorted(SUPPORTED_STACKS)


def _read_config(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise AxiomProjectError(f"{path}:{line_number}: expected key = \"value\"")

        key, value = (part.strip() for part in line.split("=", 1))
        if not key:
            raise AxiomProjectError(f"{path}:{line_number}: missing config key")
        if len(value) < 2 or value[0] != '"' or value[-1] != '"':
            raise AxiomProjectError(f"{path}:{line_number}: config values must be quoted strings")

        config[key] = value[1:-1]

    return config


def _module_name_from_project(name: str) -> str:
    return name.replace("-", "_")


def _entrypoint_code(entry: str) -> str:
    if not ENTRYPOINT_RE.fullmatch(entry):
        raise AxiomProjectError("Project entry must use module.function format")

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


def _build_static_site(project: Project, modules: list, apps: list[AppSpec]) -> list[Path]:
    index_path = project.build / "index.html"
    index_path.write_text(_static_site_html(project, modules, apps), encoding="utf-8")
    return [index_path]


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


def _static_site_html(project: Project, modules: list, apps: list[AppSpec]) -> str:
    sections: list[str] = []

    for app in apps:
        sections.append(_app_html(app))

    for module in modules:
        for function in module.functions:
            purpose = " ".join(function.purpose) if function.purpose else "No purpose provided."
            examples = "".join(f"<li><code>{escape(example)}</code></li>" for example in function.examples)
            if not examples:
                examples = "<li>No examples provided.</li>"
            sections.append(
                "\n".join(
                    [
                        '<section class="card">',
                        f"<h2>{escape(function.name)}</h2>",
                        f"<p>{escape(purpose)}</p>",
                        "<h3>Examples</h3>",
                        f"<ul>{examples}</ul>",
                        "</section>",
                    ]
                )
            )

    content = "\n".join(sections) or '<section class="card"><p>No Axiom functions found.</p></section>'

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escape(project.name)}</title>",
            "  <style>",
            "    body { font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; color: #0f172a; }",
            "    main { max-width: 760px; margin: 0 auto; }",
            "    .card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin: 1rem 0; }",
            "    code { background: #f1f5f9; padding: 0.1rem 0.3rem; border-radius: 4px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <main>",
            f"    <h1>{escape(project.name)}</h1>",
            "    <p>Generated by Axiom using the static-site stack.</p>",
            content,
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _app_html(app: AppSpec) -> str:
    parts = [
        '<section class="card">',
        f"<h2>{escape(app.name)}</h2>",
        _paragraph_list("Purpose", app.purpose),
        _paragraph_list("Requirements", app.requires),
        _paragraph_list("Actions", app.action),
        _paragraph_list("Examples", app.examples),
    ]

    for component in _iter_components(app):
        parts.append(_component_html(component))

    if app.deploy is not None:
        parts.append(_deploy_html(app.deploy))

    parts.append("</section>")
    return "\n".join(parts)


def _component_html(component: AppComponent) -> str:
    stack = escape(component.stack or "not specified")
    return "\n".join(
        [
            f"<h3>{escape(component.name.title())}</h3>",
            f"<p><strong>Stack:</strong> {stack}</p>",
            _paragraph_list("Description", component.descriptions),
        ]
    )


def _deploy_html(deploy: DeploySpec) -> str:
    target = escape(deploy.target or "not specified")
    credential_note = ""
    if deploy.credentials:
        credential_note = "<p><strong>Credentials:</strong> configured outside generated code</p>"
    return "\n".join(
        [
            "<h3>Deploy</h3>",
            f"<p><strong>Target:</strong> {target}</p>",
            _paragraph_list("Description", deploy.descriptions),
            credential_note,
        ]
    )


def _paragraph_list(title: str, items: list[str]) -> str:
    if not items:
        return ""
    rendered = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<h3>{escape(title)}</h3><ul>{rendered}</ul>"


def _iter_components(app: AppSpec) -> list[AppComponent]:
    return [component for component in [app.frontend, app.backend, app.database] if component is not None]


def _entry_module(entry: str) -> str:
    return entry.rsplit(".", 1)[0]


def _starter_source(module_name: str, stack: str) -> str:
    app_name = _app_name_from_module(module_name)
    if stack == "static-site":
        purpose = "Describe the main page of the generated site."
        frontend_stack = "static-site"
    else:
        purpose = "Start the application."
        frontend_stack = "terminal"

    return "\n".join(
        [
            f"app {app_name}:",
            "",
            "    purpose:",
            f"        {purpose}",
            "",
            "    requires:",
            "        The app should be simple to understand and safe to change.",
            "",
            "    action:",
            "        Show a friendly starter experience.",
            "",
            "    examples:",
            "        When the app runs, people can see it was generated by Axiom.",
            "",
            "    frontend:",
            f"        stack: {frontend_stack}",
            "        descriptions:",
            "            Present the starter experience clearly.",
            "",
            "    backend:",
            "        stack: none",
            "        descriptions:",
            "            No backend is required for the starter app.",
            "",
        ]
    )


def _starter_readme(name: str, stack: str) -> str:
    return "\n".join(
        [
            f"# {name}",
            "",
            f"Generated by Axiom using the `{stack}` stack.",
            "",
            "## Commands",
            "",
            "```bash",
            "axiom build",
            "axiom run",
            "```",
            "",
        ]
    )


def _unsupported_stack_message(stack: str) -> str:
    supported = ", ".join(list_stacks())
    return f"Unsupported stack {stack!r}. Supported stacks: {supported}"


def _app_name_from_module(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))
