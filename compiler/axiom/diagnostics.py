from dataclasses import dataclass

from .app import AppSpec
from .ast import FunctionDef, Module


@dataclass(frozen=True, slots=True)
class Diagnostic:
    level: str
    code: str
    message: str


def check_module(module: Module) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not module.functions:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="module.empty",
                message=f"Module {module.name!r} has no functions.",
            )
        )

    for function in module.functions:
        diagnostics.extend(_check_function(function))

    return diagnostics


def check_app(app: AppSpec) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not app.purpose:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_purpose",
                message=f"App {app.name!r} has no purpose block.",
            )
        )

    if not app.action:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_action",
                message=f"App {app.name!r} has no action block.",
            )
        )

    if not app.examples:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_examples",
                message=f"App {app.name!r} has no examples block.",
            )
        )

    if app.deploy is not None and any(not _is_safe_credential_reference(value) for value in app.deploy.credentials):
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="deploy.credentials_in_source",
                message="Deploy credentials should be referenced from environment or secrets, not stored in .ax files.",
            )
        )

    if _has_stateful_intent(app) and not app.entities:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_data_model",
                message="Stateful app intent was found, but no entities are defined. Add an entities block for stored data.",
            )
        )

    if _has_ui_intent(app) and not app.pages and not app.forms and not app.workflows and not app.examples:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_user_flows",
                message="UI intent was found, but no pages, forms, workflows, or examples describe how users move through the app.",
            )
        )

    if app.entities and not app.database and not _has_persistence_rule(app):
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.missing_persistence_rules",
                message="Entities are defined, but persistence is unclear. Add a database section or action effects such as persist/store.",
            )
        )

    if _has_auth_intent(app) and (not app.roles or not app.permissions):
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.unsafe_auth_assumption",
                message="Authentication or authorization intent was found, but roles and permissions are not defined.",
            )
        )

    if _has_ambiguous_app_intent(app):
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="app.ambiguous_definition",
                message="The app action is broad and no semantic blocks clarify data, UI, actions, or workflows.",
            )
        )

    if app.deploy is not None and _has_unclear_deployment_security(app):
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="deploy.unclear_security",
                message="Deployment intent is present, but target, description, or external credentials are unclear.",
            )
        )

    return diagnostics


def _is_safe_credential_reference(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered == "env" or lowered.startswith("env:") or lowered.startswith("secret:")


def _has_stateful_intent(app: AppSpec) -> bool:
    return app.database is not None or _contains_any(_all_app_text(app), {"persist", "store", "database", "record", "sqlite"})


def _has_ui_intent(app: AppSpec) -> bool:
    return app.frontend is not None or bool(app.pages or app.forms) or _contains_any(_all_app_text(app), {"page", "form", "screen", "button", "user"})


def _has_persistence_rule(app: AppSpec) -> bool:
    if app.database is not None:
        return True
    return any(
        _contains_any(action.effects + action.outputs + action.validations, {"persist", "store", "save", "database"})
        for action in app.app_actions
    )


def _has_auth_intent(app: AppSpec) -> bool:
    return _contains_any(
        _all_app_text(app),
        {"auth", "authenticate", "authorization", "login", "password", "permission", "role", "session", "sign in"},
    )


def _has_ambiguous_app_intent(app: AppSpec) -> bool:
    if app.entities or app.pages or app.forms or app.app_actions or app.workflows:
        return False
    action_text = " ".join(app.action).lower()
    return any(phrase in action_text for phrase in ["build an app", "build a app", "create an app", "create a app", "create a simple"])


def _has_unclear_deployment_security(app: AppSpec) -> bool:
    deploy = app.deploy
    if deploy is None:
        return False
    target = (deploy.target or "").strip().lower()
    if not target:
        return True
    if not deploy.descriptions:
        return True
    if target not in {"local", "localhost"} and not deploy.credentials:
        return True
    return False


def _all_app_text(app: AppSpec) -> list[str]:
    items = [*app.purpose, *app.requires, *app.action, *app.examples]
    for component in [app.frontend, app.backend, app.database]:
        if component is not None:
            items.extend(component.descriptions)
            items.extend(component.details.keys())
            for values in component.details.values():
                items.extend(values)
    if app.deploy is not None:
        items.extend(app.deploy.descriptions)
        items.extend(app.deploy.credentials)
        if app.deploy.target:
            items.append(app.deploy.target)
    for entity in app.entities:
        items.extend(entity.purpose)
        items.extend(entity.validations)
    for page in app.pages:
        items.extend(page.purpose)
        items.extend(page.descriptions)
    for form in app.forms:
        items.extend(form.descriptions)
        items.extend(form.validations)
    for action in app.app_actions:
        items.extend(action.purpose)
        items.extend(action.inputs)
        items.extend(action.outputs)
        items.extend(action.effects)
        items.extend(action.errors)
        items.extend(action.validations)
    for workflow in app.workflows:
        items.extend(workflow.descriptions)
        items.extend(workflow.examples)
    return items


def _contains_any(items: list[str], keywords: set[str]) -> bool:
    text = " ".join(items).lower()
    return any(keyword in text for keyword in keywords)


def _check_function(function: FunctionDef) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not function.purpose:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="function.missing_purpose",
                message=f"Function {function.name!r} has no purpose block.",
            )
        )

    if not function.action:
        diagnostics.append(
            Diagnostic(
                level="error",
                code="function.missing_action",
                message=f"Function {function.name!r} has no action block.",
            )
        )

    if not function.examples:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code="function.missing_examples",
                message=f"Function {function.name!r} has no examples block.",
            )
        )

    return diagnostics
