# Axiom Syntax

## Function example

```axiom
function add(a: Number, b: Number) -> Number:
    purpose:
        Add two numbers.

    requires:
        a >= 0
        b >= 0

    action:
        return a + b

    examples:
        add(2, 3) == 5
```

## Indentation

Axiom uses indentation to define blocks.

Recommended indentation is 4 spaces.

## Comments

Comments start with `#`.

```axiom
# This is a comment
```

## Naming

Recommended naming:

```text
modules: snake_case
functions: snake_case
types: PascalCase
variables: snake_case
```

## Collaboration metadata

Use `purpose`, `requires`, `ensures`, and `examples` to make functions easier for humans and agents to maintain.

```axiom
function can_ship(in_stock: Boolean, address_valid: Boolean) -> Boolean:
    purpose:
        Decide whether an order can be shipped.

    requires:
        address_valid == true

    action:
        return in_stock and address_valid

    examples:
        can_ship(true, true) == true
        can_ship(false, true) == false
```

Run `axiom check path/to/file.ax` to find missing intent or examples.
