# Agent Guidelines for Axiom Projects

AI agents working on Axiom projects should follow these rules. Human contributors can use the same checklist when reviewing agent-authored changes.

## Read before editing

Before editing a function, read:

1. `purpose`
2. `requires`
3. `ensures`
4. `effects`
5. `examples`
6. related tests

Also read `AGENTS.md` at the repository root when contributing to Axiom itself.

## Do not remove intent

Agents must not remove `purpose` blocks.

If behavior changes, update the purpose and examples.

## Preserve contracts

Agents should not weaken `requires` or `ensures` unless explicitly asked.

## Add examples

Every behavior change should include at least one example.

Examples should be executable when possible. Prefer examples that clarify edge cases over examples that only repeat the obvious path.

## Run checks

Before handing work back to a human reviewer, run the relevant checks:

```bash
axiom check path/to/file.ax
axiom test path/to/file.ax
pytest
```

If a check cannot run, explain why and describe the fallback used.

## Keep changes reviewable

Agents should prefer focused patches. A good agent contribution is easy for a human to summarize, test, and revert if needed.

## Respect agent policy

If an `agent_policy` exists, obey it.

Example:

```axiom
agent_policy:
    ai_can_edit:
        - examples
        - docs

    ai_cannot_edit:
        - payment_logic
        - security
```
