# Agent Contribution Guide

AI agents are welcome to contribute to Axiom.

Axiom exists to make software easier for humans and agents to understand together. Treat the source as a shared contract: preserve intent, keep behavior testable, and make changes small enough for a human reviewer to trust.

## Before Editing

1. Read `README.md`.
2. Read `docs/language-spec.md`.
3. Read `docs/agent-guidelines.md`.
4. Inspect nearby examples and tests before changing compiler behavior.

## Editing Rules

- Preserve `purpose` blocks unless the behavior truly changes.
- Do not weaken `requires` or `ensures` without an explicit reason.
- Add or update `examples` whenever behavior changes.
- Preserve app-level `frontend`, `backend`, `database`, and `deploy` intent when changing generated outputs.
- Never place raw deployment credentials in `.ax` files or generated code.
- Keep generated output deterministic and simple.
- Prefer small changes with tests over broad rewrites.
- Do not add heavy runtime dependencies without a strong reason.

## Validation

Run these checks when relevant:

```bash
axiom stacks
axiom generate examples/login_page.ax --stack fastapi-react-sqlite --output login-page
axiom build
axiom run
axiom check examples/hello.ax
axiom test examples/hello.ax
pytest
```

If `pytest` is unavailable, run focused Python checks with:

```bash
PYTHONPATH=compiler python3 -m compileall -q compiler tests
```

## Good First Tasks

- Improve syntax error messages.
- Add examples for language features.
- Add tests for parser edge cases.
- Improve the Python transpiler.
- Implement small roadmap items from `docs/roadmap.md`.

## Review Expectations

Every agent-authored change should explain:

- What changed
- Why it changed
- How it was tested
- Any behavior that remains intentionally unsupported
