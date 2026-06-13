# Axiom Syntax

## App example

```axiom
app TodoApp:
    purpose:
        Help people track tasks.

    requires:
        Users can create tasks.
        Users can complete tasks.

    action:
        Build a task tracking experience.

    examples:
        When a user adds "Buy milk", it appears in the task list.

    frontend:
        stack: react
        descriptions:
            Show active and completed tasks.

    backend:
        stack: fastapi
        descriptions:
            Provide task APIs.

    deploy:
        target: aws-ec2
        credentials:
            env
```

## Semantic app example

Use semantic blocks when the app definition should drive generated behavior beyond a starter codebase.

```axiom
app TodoApp:
    purpose:
        Help people track tasks.

    entities:
        Task:
            fields:
                title: Text
                completed: Boolean default false
            validations:
                title must not be empty

    roles:
        User:
            permissions:
                task.manage_own

    permissions:
        task.manage_own:
            allows:
                create Task
                update own Task

    pages:
        TasksPage:
            route: /tasks
            forms:
                TaskForm

    forms:
        TaskForm:
            entity: Task
            fields:
                title: Task.title
            submit_action: create_task

    actions:
        create_task:
            actor: User
            effects:
                persist Task

    workflows:
        CreateTask:
            trigger: TaskForm submitted
            steps:
                Persist task: create_task
```

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
entities: PascalCase
pages: PascalCase
forms: PascalCase
actions: snake_case
permissions: dotted.snake_case
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

Run `axiom check path/to/file.ax` to find missing intent, examples, ambiguous app definitions, missing data models, unclear user flows, unsafe auth assumptions, missing persistence rules, and unclear deployment security details.
