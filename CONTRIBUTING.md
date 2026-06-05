# Contributing to Axiom

Thank you for helping improve Axiom.

Axiom is designed for collaboration between human developers and AI agents, so contributions should be clear, testable, and easy to review.

## Project Values

- Make intent explicit.
- Keep syntax readable.
- Prefer deterministic compiler output.
- Add examples for behavior.
- Keep the prototype lightweight.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Development Workflow

1. Pick a focused change.
2. Update examples or docs if language behavior changes.
3. Add or update tests for parser, transpiler, or CLI behavior.
4. Run checks before review.

Useful commands:

```bash
axiom new todo-api
axiom build todo-api
axiom run todo-api
axiom check examples/hello.ax
axiom test examples/hello.ax
pytest
```

## Human and Agent Collaboration

Human contributors should write changes so an AI agent can inspect and verify them later.

AI contributors should write changes so a human can understand the intent without reverse-engineering the patch.

In both cases, prefer small changes with clear tests.
