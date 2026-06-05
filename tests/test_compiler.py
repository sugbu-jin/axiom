from axiom.diagnostics import check_module
from axiom.parser import AxiomSyntaxError, parse_source
from axiom.transpiler_python import generate_test_code, transpile_module


def test_parse_function():
    source = """
module math

function add(a: Number, b: Number) -> Number:
    purpose:
        Add two numbers.

    action:
        return a + b

    examples:
        add(2, 3) == 5
"""
    module = parse_source(source)

    assert module.name == "math"
    assert len(module.functions) == 1
    assert module.functions[0].name == "add"
    assert module.functions[0].parameters[0].name == "a"


def test_transpile_python():
    source = """
module math

function add(a: Number, b: Number) -> Number:
    purpose:
        Add two numbers.

    action:
        return a + b
"""
    module = parse_source(source)
    output = transpile_module(module)

    assert "def add(a, b):" in output
    assert "return a + b" in output


def test_generated_examples_run():
    source = """
module inventory

function needs_reorder(quantity: Number, reorder_level: Number) -> Boolean:
    purpose:
        Determine whether a product needs restocking.

    action:
        return quantity <= reorder_level

    examples:
        needs_reorder(5, 10) == true
        needs_reorder(20, 10) == false
"""
    module = parse_source(source)
    code = generate_test_code(module)
    namespace = {}
    exec(code, namespace)

    assert namespace["__run_axiom_examples__"]() == 2


def test_rejects_duplicate_parameters():
    source = """
module math

function add(a: Number, a: Number) -> Number:
    action:
        return a
"""

    try:
        parse_source(source)
    except AxiomSyntaxError as exc:
        assert "Duplicate parameter name" in str(exc)
    else:
        raise AssertionError("Expected duplicate parameters to fail")


def test_boolean_translation_uses_literals_only():
    source = """
module flags

function enabled() -> Boolean:
    action:
        return true

    examples:
        enabled() == true
"""
    module = parse_source(source)
    output = transpile_module(module)

    assert "return True" in output


def test_check_module_reports_missing_collaboration_metadata():
    source = """
module draft

function add(a: Number, b: Number) -> Number:
    action:
        return a + b
"""
    module = parse_source(source)
    diagnostics = check_module(module)

    assert [diagnostic.code for diagnostic in diagnostics] == [
        "function.missing_purpose",
        "function.missing_examples",
    ]
