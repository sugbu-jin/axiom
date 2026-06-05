# Axiom

Axiom is an experimental open-source programming language designed for humans and AI agents to build reliable software together.

It combines code, intent, contracts, examples, side-effect declarations, and agent permissions in one readable format.

The goal is not to replace Python, TypeScript, Rust, or Go immediately. The first goal is to create a language that humans can review confidently and AI agents can understand, modify, test, and maintain safely.

## Why Axiom exists

Most programming languages were designed mainly for human developers.

Axiom is designed for a future where human developers and AI agents work together on the same codebase.

Every important unit of code should answer:

```text
What is this?
Why does it exist?
What inputs does it accept?
What output does it promise?
What can fail?
How can we test it?
What may an AI agent safely change?
```

## Design principles

1. Explicit intent over cleverness
2. Readability for humans and AI agents
3. Built-in examples as executable tests
4. Contracts for safer changes
5. Declared side effects
6. Agent permissions as first-class project metadata
7. Multi-target transpilation

## Current status

Axiom is currently a prototype.

This repository includes:

- Early language specification
- Example `.ax` files
- Minimal parser
- Minimal Python transpiler
- Basic CLI
- Basic tests

## Why humans and agents should try it

Axiom treats intent as part of the program. A function is expected to carry its purpose, contracts, executable action, and examples close together so future edits are easier to review.

For human developers, that means less hidden context and clearer review boundaries. For AI agents, it means fewer guesses before editing and a direct way to validate behavior after a change.

Good early use cases:

- Business rules that need clear intent
- API and domain logic prototypes
- Testable specifications
- Agent-editable modules inside a larger project
- Code generation experiments targeting Python first

## Example

```axiom
module inventory

function needs_reorder(quantity: Number, reorder_level: Number) -> Boolean:
    purpose:
        Determine whether a product needs restocking.

    requires:
        quantity >= 0
        reorder_level >= 0

    action:
        return quantity <= reorder_level

    examples:
        needs_reorder(5, 10) == true
        needs_reorder(20, 10) == false
```

Generated Python:

```python
def needs_reorder(quantity, reorder_level):
    return quantity <= reorder_level
```

## Quick start

Clone this repository, then run:

```bash
cd axiom
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Transpile an example:

```bash
axiom compile examples/hello.ax
```

Run examples as tests:

```bash
axiom test examples/hello.ax
```

Check collaboration metadata:

```bash
axiom check examples/hello.ax
```

Run the repository test suite:

```bash
pytest
```

## Repository structure

```text
axiom/
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── language-spec.md
│   ├── syntax.md
│   ├── agent-guidelines.md
│   └── roadmap.md
├── examples/
│   ├── hello.ax
│   ├── inventory.ax
│   └── api.ax
├── compiler/
│   └── axiom/
│       ├── __init__.py
│       ├── ast.py
│       ├── diagnostics.py
│       ├── parser.py
│       ├── transpiler_python.py
│       └── cli.py
└── tests/
    └── test_compiler.py
```

## Proposed language roadmap

### Axiom 0.1

- `module`
- `function`
- `purpose`
- `requires`
- `action`
- `examples`
- `return`
- basic types
- Python transpiler
- example runner

### Axiom 0.2

- `type`
- `endpoint`
- `effects`
- `errors`
- better expression parser
- TypeScript transpiler

### Axiom 0.3

- OpenAPI generation
- SQL schema generation
- package metadata
- VS Code extension

## Open-source license

This project is released under the MIT License.

## Contributing

Axiom is intentionally early. Human developers and AI agents are both welcome to contribute.

Before editing:

1. Read `README.md`, `docs/language-spec.md`, and `docs/agent-guidelines.md`.
2. Run `axiom check` on any `.ax` file you change.
3. Run `axiom test` for changed examples.
4. Add or update tests when compiler behavior changes.

Good contribution areas:

- Language syntax design
- Parser implementation
- Python transpiler
- TypeScript transpiler
- Documentation
- Examples
- Agent safety model
- Developer tooling

AI agents should also read `AGENTS.md` before changing code.

## Project philosophy

Axiom code should be easy to read, easy to test, and hard to misunderstand.

The language should help AI agents make safer changes by giving them structured intent, contracts, examples, and editing boundaries.
