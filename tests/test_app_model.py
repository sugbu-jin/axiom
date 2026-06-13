from axiom.app import (
    ActionSpec,
    AppSpec,
    EntitySpec,
    FieldSpec,
    FormFieldSpec,
    FormSpec,
    PageSpec,
    PermissionSpec,
    RelationshipSpec,
    RoleSpec,
    ValidationSpec,
    WorkflowSpec,
    WorkflowStepSpec,
)


def test_app_spec_preserves_empty_semantic_defaults():
    app = AppSpec(name="TodoApp")

    assert app.entities == []
    assert app.roles == []
    assert app.permissions == []
    assert app.pages == []
    assert app.forms == []
    assert app.app_actions == []
    assert app.workflows == []
    assert app.validations == []
    assert app.integrations == []
    assert app.jobs == []
    assert app.events == []


def test_semantic_app_model_can_describe_crud_flow():
    app = AppSpec(
        name="TodoApp",
        entities=[
            EntitySpec(
                name="Task",
                purpose=["Track work a user wants to complete."],
                fields=[
                    FieldSpec(name="title", type_name="Text", validations=["must not be empty"]),
                    FieldSpec(name="completed", type_name="Boolean", default="false"),
                ],
                relationships=[RelationshipSpec(name="owner", target="User", kind="many-to-one")],
            )
        ],
        roles=[RoleSpec(name="User", permissions=["task.manage_own"])],
        permissions=[PermissionSpec(name="task.manage_own", allows=["create Task", "update own Task", "delete own Task"])],
        pages=[PageSpec(name="TasksPage", route="/tasks", forms=["TaskForm"], actions=["create_task", "complete_task"])],
        forms=[
            FormSpec(
                name="TaskForm",
                entity="Task",
                fields=[FormFieldSpec(name="title", source="Task.title")],
                submit_action="create_task",
            )
        ],
        app_actions=[
            ActionSpec(
                name="create_task",
                actor="User",
                inputs=["TaskForm"],
                outputs=["Task"],
                effects=["persist Task"],
                validations=["title must not be empty"],
            )
        ],
        workflows=[
            WorkflowSpec(
                name="CreateTask",
                trigger="TaskForm submitted",
                steps=[WorkflowStepSpec(name="Persist task", action="create_task")],
                examples=['When a user adds "Buy milk", it appears in the task list.'],
            )
        ],
        validations=[ValidationSpec(name="TaskTitleRequired", rule="Task.title != ''", applies_to=["Task.title"])],
    )

    assert app.entities[0].fields[0].name == "title"
    assert app.roles[0].permissions == ["task.manage_own"]
    assert app.pages[0].route == "/tasks"
    assert app.forms[0].submit_action == "create_task"
    assert app.workflows[0].steps[0].action == "create_task"
