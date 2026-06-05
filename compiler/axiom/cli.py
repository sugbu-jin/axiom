import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .app_parser import AxiomAppSyntaxError, is_app_source, parse_app_source
from .diagnostics import check_app, check_module
from .parser import AxiomSyntaxError, parse_file
from .project import AxiomProjectError, build_project, create_project, generate_project, list_stacks, run_project
from .transpiler_python import generate_test_code, transpile_module


def compile_command(args: argparse.Namespace) -> int:
    module = parse_file(args.file)
    output = transpile_module(module)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    return 0


def test_command(args: argparse.Namespace) -> int:
    module = parse_file(args.file)
    code = generate_test_code(module)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / f"{module.name}_examples.py"
        tmp_path.write_text(code, encoding="utf-8")
        result = subprocess.run([sys.executable, str(tmp_path)], text=True)

    return result.returncode


def check_command(args: argparse.Namespace) -> int:
    path = Path(args.file)
    source = path.read_text(encoding="utf-8")
    if is_app_source(source):
        diagnostics = check_app(parse_app_source(source))
    else:
        diagnostics = check_module(parse_file(path))

    if not diagnostics:
        print("No issues found.")
        return 0

    for diagnostic in diagnostics:
        print(f"{diagnostic.level}: {diagnostic.code}: {diagnostic.message}")

    return 1 if any(diagnostic.level == "error" for diagnostic in diagnostics) else 0


def new_command(args: argparse.Namespace) -> int:
    path = create_project(args.name, parent=args.directory, stack=args.stack)
    print(f"Created Axiom project at {path}")
    return 0


def generate_command(args: argparse.Namespace) -> int:
    generated = generate_project(args.file, output=args.output, stack=args.stack)
    print(f"Generated app at {generated.root}")
    print("")
    for output in generated.outputs:
        print(f"created: {output}")
    print("")
    print("\n".join(generated.next_steps))
    return 0


def build_command(args: argparse.Namespace) -> int:
    outputs = build_project(args.project)
    for output in outputs:
        print(output)
    return 0


def run_command(args: argparse.Namespace) -> int:
    return run_project(args.project)


def stacks_command(args: argparse.Namespace) -> int:
    for stack in list_stacks():
        print(stack)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axiom", description="Axiom prototype CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="Transpile an Axiom file to Python")
    compile_parser.add_argument("file")
    compile_parser.add_argument("-o", "--output")
    compile_parser.set_defaults(func=compile_command)

    test_parser = subparsers.add_parser("test", help="Run Axiom examples as tests")
    test_parser.add_argument("file")
    test_parser.set_defaults(func=test_command)

    check_parser = subparsers.add_parser("check", help="Check an Axiom file for collaboration metadata")
    check_parser.add_argument("file")
    check_parser.set_defaults(func=check_command)

    new_parser = subparsers.add_parser("new", help="Create a new Axiom project")
    new_parser.add_argument("name")
    new_parser.add_argument("-d", "--directory", default=".")
    new_parser.add_argument("--stack", default="python-cli", choices=list_stacks())
    new_parser.set_defaults(func=new_command)

    generate_parser = subparsers.add_parser("generate", help="Generate an app directly from a .ax file")
    generate_parser.add_argument("file")
    generate_parser.add_argument("--stack", default="python-cli", choices=list_stacks())
    generate_parser.add_argument("-o", "--output")
    generate_parser.set_defaults(func=generate_command)

    build_project_parser = subparsers.add_parser("build", help="Build an Axiom project")
    build_project_parser.add_argument("project", nargs="?", default=".")
    build_project_parser.set_defaults(func=build_command)

    run_parser = subparsers.add_parser("run", help="Build and run an Axiom project")
    run_parser.add_argument("project", nargs="?", default=".")
    run_parser.set_defaults(func=run_command)

    stacks_parser = subparsers.add_parser("stacks", help="List supported project stacks")
    stacks_parser.set_defaults(func=stacks_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except (AxiomAppSyntaxError, AxiomProjectError, AxiomSyntaxError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
