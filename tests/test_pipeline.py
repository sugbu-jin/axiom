from pathlib import Path
import tempfile

from axiom.pipeline import build_app_plan, infer_stack, parse_project_sources


def test_parse_project_sources_separates_apps_and_modules():
    app_source = """
app TodoApp:
    purpose:
        Help people track tasks.

    action:
        Create a task app.
"""
    module_source = """
module math

function add(a: Number, b: Number) -> Number:
    action:
        return a + b
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        app_path = root / "app.ax"
        module_path = root / "math.ax"
        app_path.write_text(app_source, encoding="utf-8")
        module_path.write_text(module_source, encoding="utf-8")

        parsed_project = parse_project_sources([module_path, app_path])

    assert [app.name for app in parsed_project.apps] == ["TodoApp"]
    assert [module.name for module in parsed_project.modules] == ["math"]


def test_build_app_plan_detects_semantic_capabilities():
    app_source = """
app TodoApp:
    purpose:
        Help people track tasks.

    entities:
        Task:
            fields:
                title: Text

    roles:
        User:
            permissions:
                task.manage_own

    pages:
        TasksPage:
            route: /tasks

    actions:
        create_task:
            effects:
                persist Task

    integrations:
        Email:
            provider: smtp

    jobs:
        DailyDigest:
            schedule: daily

    events:
        TaskCreated:
            payload:
                task_id: Text

    deploy:
        target: local
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        app_path = Path(tmpdir) / "app.ax"
        app_path.write_text(app_source, encoding="utf-8")
        app = parse_project_sources([app_path]).apps[0]

    plan = build_app_plan(app, stack="fastapi-react-sqlite")

    assert plan.stack == "fastapi-react-sqlite"
    assert plan.generator == "fastapi-react-sqlite"
    assert plan.semantic_app.capabilities == [
        "authorization",
        "background-jobs",
        "data-model",
        "deployment",
        "events",
        "integration",
        "persistence",
        "user-interface",
        "workflow",
    ]


def test_infer_stack_selects_full_stack_for_stateful_web_app():
    app_source = """
app TodoApp:
    purpose:
        Help people track tasks.

    entities:
        Task:
            fields:
                title: Text

    pages:
        TasksPage:
            route: /tasks

    actions:
        create_task:
            effects:
                persist Task
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        app_path = Path(tmpdir) / "app.ax"
        app_path.write_text(app_source, encoding="utf-8")
        parsed_project = parse_project_sources([app_path])

    stack_plan = infer_stack(parsed_project, requested_stack="auto")

    assert stack_plan.selected_stack == "fastapi-react-sqlite"
    assert stack_plan.inferred is True
    assert "data-model" in stack_plan.capabilities
    assert "persistence" in stack_plan.capabilities
    assert "user-interface" in stack_plan.capabilities


def test_infer_stack_preserves_explicit_stack():
    app_source = """
app LandingPage:
    purpose:
        Explain a product.

    frontend:
        stack: static-site
        descriptions:
            Show product content.
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        app_path = Path(tmpdir) / "app.ax"
        app_path.write_text(app_source, encoding="utf-8")
        parsed_project = parse_project_sources([app_path])

    stack_plan = infer_stack(parsed_project, requested_stack="python-cli")

    assert stack_plan.selected_stack == "python-cli"
    assert stack_plan.inferred is False
    assert stack_plan.reasons == ["Stack was explicitly configured as python-cli."]
