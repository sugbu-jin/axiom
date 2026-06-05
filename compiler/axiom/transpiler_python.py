import re

from .ast import FunctionDef, Module


BOOLEAN_LITERAL_RE = re.compile(r"\b(true|false)\b")
BOOLEAN_LITERALS = {"true": "True", "false": "False"}


def _translate_expr(expr: str) -> str:
    return BOOLEAN_LITERAL_RE.sub(lambda match: BOOLEAN_LITERALS[match.group(1)], expr)


def transpile_function(function: FunctionDef) -> str:
    params = ", ".join(param.name for param in function.parameters)
    lines = [f"def {function.name}({params}):"]

    if function.purpose:
        doc = " ".join(function.purpose)
        lines.append(f"    {doc!r}")

    for requirement in function.requires:
        expression = _translate_expr(requirement)
        message = f"Requirement failed: {requirement}"
        lines.append(f"    assert {expression}, {message!r}")

    if function.action:
        lines.extend(f"    {_translate_expr(statement)}" for statement in function.action)
    else:
        lines.append("    pass")

    return "\n".join(lines)


def transpile_module(module: Module) -> str:
    lines = [f"# Generated from Axiom module: {module.name}", ""]

    for function in module.functions:
        lines.append(transpile_function(function))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_test_code(module: Module) -> str:
    code = transpile_module(module)
    test_lines = [code, "", "def __run_axiom_examples__():"]
    example_count = 0

    for function in module.functions:
        for example in function.examples:
            example_count += 1
            expression = _translate_expr(example)
            message = f"Example failed: {example}"
            test_lines.append(f"    assert {expression}, {message!r}")

    if example_count == 0:
        test_lines.append("    return 0")
    else:
        test_lines.append(f"    return {example_count}")

    test_lines.extend(
        [
            "",
            "if __name__ == '__main__':",
            "    count = __run_axiom_examples__()",
            "    print(f'Passed {count} Axiom example(s).')",
        ]
    )

    return "\n".join(test_lines) + "\n"
