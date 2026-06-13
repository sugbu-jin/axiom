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

### app

Declares an application that can be described by intent first and technical details second.

```axiom
app TodoApp:
```

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

An app intended for shared human and AI maintenance should include:

```axiom
app TodoApp:
    purpose:
        Help people track tasks.

    requires:
        Users can create tasks.
        Users can mark tasks as done.
        Tasks should persist after refresh.

    action:
        Create a simple task tracking application.

    examples:
        When a user adds "Buy milk", it appears in the task list.

    frontend:
        stack: react
        descriptions:
            Show a clean task list.

    backend:
        stack: fastapi
        descriptions:
            Provide APIs for tasks.

    database:
        stack: sqlite
        descriptions:
            Store task records.

    deploy:
        target: aws-ec2
        descriptions:
            Deploy the generated app to an EC2 server.
        credentials:
            env
```

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

The current function-level Python transpiler executes `requires`, `action`, and `examples`. The parser preserves `ensures` so future compiler passes can enforce postconditions.

The current app-level project builder parses `purpose`, `requires`, `action`, `examples`, `frontend`, `backend`, `database`, `deploy`, and semantic app blocks. Generators use those sections to produce stack-specific outputs.

Credentials should not be stored directly in `.ax` files. Use references such as `env` or a future secrets provider.

## Semantic app blocks

Semantic app blocks let non-programmers describe the app itself before choosing a technical stack. These blocks are parsed into a semantic app model and used by diagnostics and stack inference.

```axiom
app TodoApp:
    purpose:
        Help people track tasks.

    entities:
        Task:
            purpose:
                Track work a user wants to complete.
            fields:
                title: Text
                completed: Boolean default false
            relationships:
                owner: User many-to-one
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
            actions:
                create_task

    forms:
        TaskForm:
            entity: Task
            fields:
                title: Task.title
            submit_action: create_task

    actions:
        create_task:
            actor: User
            inputs:
                TaskForm
            outputs:
                Task
            effects:
                persist Task
            validations:
                title must not be empty

    workflows:
        CreateTask:
            trigger: TaskForm submitted
            steps:
                Persist task: create_task
            examples:
                When a user adds "Buy milk", it appears in the task list.
```

Supported semantic sections:

- `entities`: Stored or business objects such as `Task`, `User`, or `Order`.
- `fields`: Entity fields such as `title: Text`, `email: Text unique`, or `completed: Boolean default false`.
- `relationships`: Links between entities such as `owner: User many-to-one`.
- `roles` and `permissions`: Who can do what.
- `pages` and `forms`: User-facing screens and inputs.
- `actions`: App-level commands such as `create_task`, including actor, inputs, outputs, effects, errors, and validations.
- `workflows`: Multi-step user or system flows.
- `validations`: Named rules that apply to fields or entities.
- `integrations`: External providers and capability/credential references.
- `jobs`: Scheduled or background work.
- `events`: Domain events and their payloads.

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
stack = "auto"
source = "src"
build = "build"
entry = "todo_api.main"
```

The current project workflow is intentionally small:

```bash
axiom generate examples/login_page.ax --stack fastapi-react-sqlite --output login-page
axiom new todo-api
axiom new landing-page --stack static-site
axiom build todo-api
axiom run todo-api
```

`axiom generate` is the easiest path for non-programmers: it takes one `.ax` file, creates a project, builds generated files, and writes a `NEXT_STEPS.txt` guide. `axiom build` transpiles `.ax` files from `source` into files under `build`. `axiom run` builds the project and executes or explains how to run the selected stack.

## Stack targets

A stack target controls how Axiom turns app intent into runnable files.

Current stack targets:

- `auto`: Infers a supported target from the parsed app capabilities and writes `build/axiom-stack-plan.json`.
- `fastapi-react-sqlite`: Generates a FastAPI backend, React frontend, and SQLite-backed login-capable app shell.
- `python-cli`: Generates Python modules and a `build/__main__.py` entrypoint.
- `static-site`: Generates a dependency-free `build/index.html` page from module and function intent.

Future stack targets may generate APIs, full-stack web apps, mobile apps, or database-backed systems while keeping the `.ax` source focused on app purpose, data, actions, examples, and permissions.

## Diagnostics

`axiom check` reports missing or risky app structure for non-programmer-authored definitions. Current app diagnostics include:

- Missing purpose, action, or examples.
- Stateful app intent without `entities`.
- UI intent without pages, forms, workflows, or examples.
- Entities without clear persistence rules.
- Login, password, role, or permission intent without explicit roles and permissions.
- Broad app actions without semantic blocks that clarify the app definition.
- Deployment sections without target, description, or external credential references.

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
