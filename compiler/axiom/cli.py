import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .diagnostics import check_module
from .parser import AxiomSyntaxError, parse_file
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
    module = parse_file(args.file)
    diagnostics = check_module(module)

    if not diagnostics:
        print("No issues found.")
        return 0

    for diagnostic in diagnostics:
        print(f"{diagnostic.level}: {diagnostic.code}: {diagnostic.message}")

    return 1 if any(diagnostic.level == "error" for diagnostic in diagnostics) else 0


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except AxiomSyntaxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
