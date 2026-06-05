import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .parser import parse_file
from .transpiler_python import transpile_module


PROJECT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
ENTRYPOINT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$")
CONFIG_FILE = "axiom.toml"


class AxiomProjectError(Exception):
    """Raised when an Axiom project cannot be created, built, or run."""


@dataclass(frozen=True, slots=True)
class Project:
    root: Path
    name: str
    source: Path
    build: Path
    entry: str


def create_project(name: str, parent: str | Path = ".") -> Path:
    if not PROJECT_NAME_RE.fullmatch(name):
        raise AxiomProjectError(
            "Project name must start with a letter and contain only letters, numbers, hyphens, or underscores."
        )

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
                'source = "src"',
                'build = "build"',
                f'entry = "{module_name}.main"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (source_dir / "main.ax").write_text(_starter_source(module_name), encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(name), encoding="utf-8")

    return root


def load_project(path: str | Path = ".") -> Project:
    root = Path(path).resolve()
    config_path = root / CONFIG_FILE
    if not config_path.exists():
        raise AxiomProjectError(f"Missing {CONFIG_FILE} in {root}")

    config = _read_config(config_path)
    name = config.get("name", root.name)
    source = root / config.get("source", "src")
    build = root / config.get("build", "build")
    entry = config.get("entry", f"{_module_name_from_project(name)}.main")

    return Project(root=root, name=name, source=source, build=build, entry=entry)


def build_project(path: str | Path = ".") -> list[Path]:
    project = load_project(path)
    if not project.source.exists():
        raise AxiomProjectError(f"Missing source directory: {project.source}")

    source_files = sorted(project.source.rglob("*.ax"))
    if not source_files:
        raise AxiomProjectError(f"No .ax source files found in {project.source}")

    project.build.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    for source_file in source_files:
        module = parse_file(source_file)
        output_path = project.build / f"{module.name}.py"
        output_path.write_text(transpile_module(module), encoding="utf-8")
        outputs.append(output_path)

    main_path = project.build / "__main__.py"
    main_path.write_text(_entrypoint_code(project.entry), encoding="utf-8")
    outputs.append(main_path)

    return outputs


def run_project(path: str | Path = ".") -> int:
    project = load_project(path)
    build_project(project.root)
    result = subprocess.run([sys.executable, "__main__.py"], cwd=project.build, text=True)
    return result.returncode


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


def _starter_source(module_name: str) -> str:
    return "\n".join(
        [
            f"module {module_name}",
            "",
            "function main() -> Void:",
            "    purpose:",
            "        Start the application.",
            "",
            "    action:",
            '        print("Hello from Axiom.")',
            "",
            "    examples:",
            "        true == true",
            "",
        ]
    )


def _starter_readme(name: str) -> str:
    return "\n".join(
        [
            f"# {name}",
            "",
            "Generated by Axiom.",
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
