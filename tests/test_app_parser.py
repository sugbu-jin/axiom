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
