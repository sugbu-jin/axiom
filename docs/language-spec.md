# Axiom Specification Draft

Version: 0.1 draft

## Purpose

Axiom is a programming language designed for collaboration between human developers and AI agents.

It prioritizes explicit intent, predictable syntax, contracts, examples, and declared side effects.

The language is optimized for source code that can answer these questions before an edit begins:

- What is this unit responsible for?
- What behavior must not change?
- What examples prove the behavior?
- What side effects or permissions are involved?
- What can a human or AI agent safely modify?

## File extension

```text
.ax
```

## Core blocks

### module

Declares the module name.

```axiom
module inventory
```

### function

Declares a function.

```axiom
function add(a: Number, b: Number) -> Number:
```

### purpose

Human and AI-readable intent.

```axiom
purpose:
    Add two numbers.
```

### requires

Preconditions that must be true before execution.

```axiom
requires:
    amount >= 0
```

### ensures

Postconditions that should be true after execution.

```axiom
ensures:
    result >= 0
```

### action

Executable body.

```axiom
action:
    return a + b
```

### examples

Executable examples.

```axiom
examples:
    add(2, 3) == 5
```

Examples are part of the collaboration contract. They should cover normal behavior and important edge cases so agents can validate their edits without guessing.

## Collaboration expectations

A function intended for shared human and AI maintenance should include:

```axiom
function needs_reorder(quantity: Number, reorder_level: Number) -> Boolean:
    purpose:
        Determine whether inventory should be reordered.

    requires:
        quantity >= 0
        reorder_level >= 0

    ensures:
        result == true or result == false

    action:
        return quantity <= reorder_level

    examples:
        needs_reorder(5, 10) == true
        needs_reorder(20, 10) == false
```

The current Python transpiler executes `requires`, `action`, and `examples`. The parser preserves `ensures` so future compiler passes can enforce postconditions.

## Project layout

Axiom projects use a small configuration file and a `src` directory:

```text
todo-api/
    axiom.toml
    src/
        main.ax
    build/
        __main__.py
        todo_api.py
```

The initial project configuration is:

```toml
name = "todo-api"
source = "src"
build = "build"
entry = "todo_api.main"
```

The current project workflow is intentionally small:

```bash
axiom new todo-api
axiom build todo-api
axiom run todo-api
```

`axiom build` transpiles `.ax` files from `source` into Python files under `build`. `axiom run` builds the project and executes the configured entry function.

## Primitive types

Initial types:

```text
Text
Number
Boolean
Money
```

## Boolean literals

```text
true
false
```

These transpile to Python as:

```python
True
False
```

## Future blocks

Planned but not fully implemented:

```axiom
type Product:
    id: Text
    name: Text

endpoint GET /products/{id}:
    purpose:
        Return product details.

agent_policy:
    ai_can_edit:
        - examples
        - action
```
