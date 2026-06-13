from axiom.app_parser import parse_app_source
from axiom.diagnostics import check_app


def test_parse_app_with_optional_stack_details():
    source = """
app TodoApp:
    purpose:
        Help people track tasks.

    requires:
        Users can create tasks.
        Users can mark tasks as done.

    action:
        Create a simple task tracking app.

    examples:
        When a user adds "Buy milk", it appears in the task list.

    frontend:
        stack: react
        descriptions:
            Show a clean task list.
            Include an input for adding new tasks.

    backend:
        stack: fastapi
        descriptions:
            Provide APIs for tasks.

    database:
        stack: sqlite
        descriptions:
            Store tasks locally.

    deploy:
        target: aws-ec2
        descriptions:
            Deploy the generated app to an EC2 server.
        credentials:
            env
"""

    app = parse_app_source(source)

    assert app.name == "TodoApp"
    assert app.purpose == ["Help people track tasks."]
    assert app.frontend is not None
    assert app.frontend.stack == "react"
    assert app.backend is not None
    assert app.backend.stack == "fastapi"
    assert app.database is not None
    assert app.database.stack == "sqlite"
    assert app.deploy is not None
    assert app.deploy.target == "aws-ec2"
    assert app.deploy.credentials == ["env"]
    assert "deploy.credentials_in_source" not in [diagnostic.code for diagnostic in check_app(app)]


def test_check_app_warns_about_credentials_in_source():
    source = """
app TodoApp:
    purpose:
        Help people track tasks.

    deploy:
        target: aws-ec2
        credentials:
            AKIA...
"""

    app = parse_app_source(source)
    diagnostics = check_app(app)

    assert "deploy.credentials_in_source" in [diagnostic.code for diagnostic in diagnostics]


def test_check_app_warns_about_missing_non_programmer_structure():
    source = """
app InventoryApp:
    purpose:
        Help staff manage inventory.

    action:
        Create a simple inventory app.

    frontend:
        stack: react
        descriptions:
            Show a screen for staff users.

    backend:
        stack: fastapi
        descriptions:
            Store inventory records.

    database:
        stack: sqlite

    deploy:
        target: aws-ec2
"""

    app = parse_app_source(source)
    diagnostics = check_app(app)
    codes = [diagnostic.code for diagnostic in diagnostics]

    assert "app.missing_data_model" in codes
    assert "app.missing_user_flows" in codes
    assert "app.ambiguous_definition" in codes
    assert "deploy.unclear_security" in codes


def test_check_app_warns_about_auth_without_roles_and_permissions():
    source = """
app LoginApp:
    purpose:
        Let users sign in.

    action:
        Create a login page with password authentication.

    examples:
        When a valid user signs in, they reach the dashboard.

    backend:
        stack: fastapi
        descriptions:
            Validate passwords before creating a session.
"""

    app = parse_app_source(source)
    diagnostics = check_app(app)

    assert "app.unsafe_auth_assumption" in [diagnostic.code for diagnostic in diagnostics]


def test_parse_app_with_semantic_blocks():
    source = """
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

    validations:
        TaskTitleRequired:
            rule: Task.title != ""
            applies_to:
                Task.title

    integrations:
        Email:
            provider: smtp
            capabilities:
                send notifications
            credentials:
                env:SMTP_PASSWORD

    jobs:
        DailyDigest:
            schedule: daily
            action: send_task_digest

    events:
        TaskCreated:
            payload:
                task_id: Text
            descriptions:
                Raised after a task is created.
"""

    app = parse_app_source(source)

    assert app.entities[0].name == "Task"
    assert app.entities[0].fields[0].name == "title"
    assert app.entities[0].fields[1].default == "false"
    assert app.entities[0].relationships[0].target == "User"
    assert app.roles[0].permissions == ["task.manage_own"]
    assert app.permissions[0].allows == ["create Task", "update own Task"]
    assert app.pages[0].route == "/tasks"
    assert app.pages[0].forms == ["TaskForm"]
    assert app.forms[0].fields[0].source == "Task.title"
    assert app.app_actions[0].effects == ["persist Task"]
    assert app.workflows[0].steps[0].action == "create_task"
    assert app.validations[0].rule == 'Task.title != ""'
    assert app.integrations[0].credentials == ["env:SMTP_PASSWORD"]
    assert app.jobs[0].schedule == "daily"
    assert app.events[0].payload[0].name == "task_id"


def test_check_app_accepts_semantic_structure_for_stateful_ui_flow():
    source = """
app TodoApp:
    purpose:
        Help people track tasks.

    examples:
        When a user adds "Buy milk", it appears in the task list.

    entities:
        Task:
            fields:
                title: Text

    roles:
        User:
            permissions:
                task.manage_own

    permissions:
        task.manage_own:
            allows:
                create Task

    pages:
        TasksPage:
            route: /tasks

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

    deploy:
        target: local
        descriptions:
            Run locally for review.
        credentials:
            env
"""

    app = parse_app_source(source)
    diagnostics = check_app(app)
    codes = [diagnostic.code for diagnostic in diagnostics]

    assert "app.missing_data_model" not in codes
    assert "app.missing_user_flows" not in codes
    assert "app.missing_persistence_rules" not in codes
    assert "app.unsafe_auth_assumption" not in codes
    assert "deploy.unclear_security" not in codes
