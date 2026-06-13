import re
import subprocess
import sys
from dataclasses import dataclass
from json import dumps, loads
from pathlib import Path

from .app_parser import is_app_source, parse_app_source
from .generators import get_generator, list_generator_stacks
from .generators.base import AxiomGeneratorError, BuildContext
from .pipeline import StackPlan, infer_stack, parse_project_sources


PROJECT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
CONFIG_FILE = "axiom.toml"
AUTO_STACK = "auto"
DEFAULT_STACK = "python-cli"
STACK_PLAN_FILE = "axiom-stack-plan.json"
SUPPORTED_STACKS = {AUTO_STACK, *list_generator_stacks()}


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


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    root: Path
    outputs: list[Path]
    next_steps: list[str]


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
        _project_config(name, stack, module_name),
        encoding="utf-8",
    )
    (source_dir / "main.ax").write_text(_starter_source(module_name, stack), encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(name, stack), encoding="utf-8")

    return root


def generate_project(source: str | Path, output: str | Path | None = None, stack: str = DEFAULT_STACK) -> GeneratedProject:
    source_path = Path(source)
    if not source_path.exists():
        raise AxiomProjectError(f"Source file does not exist: {source_path}")
    if source_path.suffix != ".ax":
        raise AxiomProjectError("Axiom source files must use the .ax extension")
    if stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    source_text = source_path.read_text(encoding="utf-8")
    project_name = _project_name_from_source(source_path, source_text)
    root = Path(output) if output is not None else Path(project_name)
    if root.exists() and any(root.iterdir()):
        raise AxiomProjectError(f"Output directory already exists and is not empty: {root}")

    root.mkdir(parents=True, exist_ok=True)
    module_name = _module_name_from_project(project_name)
    source_dir = root / "src"
    source_dir.mkdir(parents=True, exist_ok=True)

    (root / CONFIG_FILE).write_text(_project_config(project_name, stack, module_name), encoding="utf-8")
    (source_dir / "main.ax").write_text(source_text, encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(project_name, stack), encoding="utf-8")

    outputs = build_project(root)
    selected_stack = _read_selected_stack(load_project(root))
    next_steps = _next_steps(root, selected_stack)
    (root / "NEXT_STEPS.txt").write_text("\n".join(next_steps) + "\n", encoding="utf-8")

    return GeneratedProject(root=root, outputs=outputs, next_steps=next_steps)


def load_project(path: str | Path = ".") -> Project:
    root = Path(path).resolve()
    config_path = root / CONFIG_FILE
    if not config_path.exists():
        raise AxiomProjectError(f"Missing {CONFIG_FILE} in {root}")

    config = _read_config(config_path)
    name = config.get("name", root.name)
    stack = config.get("stack", AUTO_STACK)
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
    parsed_project = parse_project_sources(source_files)
    apps = parsed_project.apps
    modules = parsed_project.modules
    stack_plan = infer_stack(parsed_project, project.stack)
    _write_stack_plan(project, stack_plan)
    stack = stack_plan.selected_stack
    generator = get_generator(stack)
    if generator is None:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    context = BuildContext(root=project.root, name=project.name, build=project.build, entry=project.entry)
    try:
        return generator.build(context, modules, apps)
    except AxiomGeneratorError as exc:
        raise AxiomProjectError(str(exc)) from exc


def run_project(path: str | Path = ".") -> int:
    project = load_project(path)
    build_project(project.root)
    stack = _read_selected_stack(project)

    if stack == "static-site":
        index_path = project.build / "index.html"
        print(f"Static site built at {index_path}")
        return 0
    if stack == "fastapi-react-sqlite":
        print(f"Full-stack app generated at {project.build}")
        print("Backend:  cd build/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload")
        print("Frontend: cd build/frontend && npm install && npm run dev")
        return 0

    result = subprocess.run([sys.executable, "__main__.py"], cwd=project.build, text=True)
    return result.returncode


def list_stacks() -> list[str]:
    return sorted(SUPPORTED_STACKS)


def _write_stack_plan(project: Project, stack_plan: StackPlan) -> Path:
    plan_path = project.build / STACK_PLAN_FILE
    plan_path.write_text(
        dumps(
            {
                "requested_stack": stack_plan.requested_stack,
                "selected_stack": stack_plan.selected_stack,
                "inferred": stack_plan.inferred,
                "capabilities": stack_plan.capabilities,
                "reasons": stack_plan.reasons,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return plan_path


def _read_selected_stack(project: Project) -> str:
    plan_path = project.build / STACK_PLAN_FILE
    if not plan_path.exists():
        return project.stack

    data = loads(plan_path.read_text(encoding="utf-8"))
    selected_stack = data.get("selected_stack", project.stack)
    if selected_stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(selected_stack))
    return selected_stack


def _next_steps(root: Path, stack: str) -> list[str]:
    lines = [
        f"Your Axiom app was generated at: {root}",
        "",
        "What to do next:",
    ]

    if stack == "fastapi-react-sqlite":
        lines.extend(
            [
                "1. Start the backend:",
                "   cd build/backend",
                "   python3 -m venv .venv",
                "   source .venv/bin/activate",
                "   pip install -r requirements.txt",
                "   uvicorn main:app --reload",
                "",
                "2. In a second terminal, start the frontend:",
                "   cd build/frontend",
                "   npm install",
                "   npm run dev",
                "",
                "3. Sign in with the demo account:",
                "   email: demo@example.com",
                "   password: password",
            ]
        )
    elif stack == "static-site":
        lines.extend(
            [
                "1. Open this file in your browser:",
                "   build/index.html",
            ]
        )
    else:
        lines.extend(
            [
                "1. Run the generated app:",
                "   axiom run",
            ]
        )

    return lines


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


def _project_config(name: str, stack: str, module_name: str) -> str:
    return "\n".join(
        [
            f'name = "{name}"',
            f'stack = "{stack}"',
            'source = "src"',
            'build = "build"',
            f'entry = "{module_name}.main"',
            "",
        ]
    )


def _project_name_from_source(source_path: Path, source_text: str) -> str:
    if is_app_source(source_text):
        app = parse_app_source(source_text)
        return _slug_from_name(app.name)
    return _slug_from_name(source_path.stem)


def _slug_from_name(name: str) -> str:
    words = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)", name.replace("_", " ").replace("-", " "))
    slug = "-".join(word.lower() for word in words if word)
    return slug or "axiom-app"


def _module_name_from_project(name: str) -> str:
    return name.replace("-", "_")


def _starter_source(module_name: str, stack: str) -> str:
    app_name = _app_name_from_module(module_name)
    if stack == "fastapi-react-sqlite":
        return _starter_login_source(app_name)
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


def _starter_login_source(app_name: str) -> str:
    return "\n".join(
        [
            f"app {app_name}:",
            "    purpose:",
            "        Let users sign in securely before accessing a protected app.",
            "",
            "    requires:",
            "        Users can enter an email and password.",
            "        Passwords are never stored as plain text.",
            "        Failed login attempts show a clear error message.",
            "",
            "    action:",
            "        Create a login page connected to a SQLite-backed user store.",
            "",
            "    examples:",
            "        When a user enters a valid email and password, they reach the dashboard.",
            "",
            "    frontend:",
            "        stack: react",
            "        descriptions:",
            "            Show a centered login form with email and password fields.",
            "",
            "    backend:",
            "        stack: fastapi",
            "        descriptions:",
            "            Provide an endpoint for login requests.",
            "",
            "    database:",
            "        stack: sqlite",
            "        descriptions:",
            "            Store users with id, email, password_hash, and created_at fields.",
            "",
            "    deploy:",
            "        target: local",
            "        credentials:",
            "            env",
            "",
        ]
    )
