import re
from pathlib import Path

from .app import (
    ActionSpec,
    AppComponent,
    AppSpec,
    DeploySpec,
    EntitySpec,
    EventSpec,
    FieldSpec,
    FormFieldSpec,
    FormSpec,
    IntegrationSpec,
    JobSpec,
    PageSpec,
    PermissionSpec,
    RelationshipSpec,
    RoleSpec,
    ValidationSpec,
    WorkflowSpec,
    WorkflowStepSpec,
)


IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
APP_RE = re.compile(rf"^app\s+(?P<name>{IDENTIFIER})\s*:$")
APP_TEXT_BLOCKS = {"purpose", "requires", "action", "examples"}
APP_SECTIONS = {"frontend", "backend", "database", "deploy"}
APP_SEMANTIC_SECTIONS = {
    "entities",
    "roles",
    "permissions",
    "pages",
    "forms",
    "actions",
    "workflows",
    "validations",
    "integrations",
    "jobs",
    "events",
}
COMPONENT_TEXT_KEYS = {"description", "descriptions", "requires", "action", "examples"}


class AxiomAppSyntaxError(Exception):
    """Raised when source cannot be parsed as an Axiom app specification."""


def is_app_source(source: str) -> bool:
    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped.startswith("app ")
    return False


def parse_app_file(path: str | Path) -> AppSpec:
    return parse_app_source(Path(path).read_text(encoding="utf-8"))


def parse_app_source(source: str) -> AppSpec:
    app: AppSpec | None = None
    active_app_block: str | None = None
    active_section: str | None = None
    active_section_key: str | None = None
    active_semantic_item: object | None = None

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = _indent_width(raw_line)

        if indent == 0:
            app_match = APP_RE.match(stripped)
            if not app_match:
                raise AxiomAppSyntaxError(f"Line {line_number}: expected app declaration")
            if app is not None:
                raise AxiomAppSyntaxError(f"Line {line_number}: only one app declaration is supported per file")

            app = AppSpec(name=app_match.group("name"))
            active_app_block = None
            active_section = None
            active_section_key = None
            active_semantic_item = None
            continue

        if app is None:
            raise AxiomAppSyntaxError(f"Line {line_number}: app content before app declaration")

        if indent == 4:
            block_name = stripped.removesuffix(":")
            if stripped.endswith(":") and block_name in APP_TEXT_BLOCKS:
                active_app_block = block_name
                active_section = None
                active_section_key = None
                active_semantic_item = None
                continue
            if stripped.endswith(":") and block_name in APP_SECTIONS:
                active_app_block = None
                active_section = block_name
                active_section_key = None
                active_semantic_item = None
                _ensure_section(app, block_name)
                continue
            if stripped.endswith(":") and block_name in APP_SEMANTIC_SECTIONS:
                active_app_block = None
                active_section = block_name
                active_section_key = None
                active_semantic_item = None
                continue
            raise AxiomAppSyntaxError(f"Line {line_number}: unknown app block: {stripped}")

        if active_app_block is not None:
            if indent < 8:
                raise AxiomAppSyntaxError(f"Line {line_number}: expected content inside {active_app_block}")
            getattr(app, active_app_block).append(stripped)
            continue

        if active_section is None:
            raise AxiomAppSyntaxError(f"Line {line_number}: section content without an active section")

        if active_section in APP_SEMANTIC_SECTIONS:
            if indent == 8:
                active_semantic_item = _create_semantic_item(app, active_section, stripped, line_number)
                active_section_key = None
                continue
            if indent == 12 and active_semantic_item is not None:
                active_section_key = _parse_semantic_item_line(active_section, active_semantic_item, stripped, line_number)
                continue
            if indent >= 16 and active_semantic_item is not None and active_section_key is not None:
                _append_semantic_item_detail(active_section, active_semantic_item, active_section_key, stripped)
                continue
            raise AxiomAppSyntaxError(f"Line {line_number}: unexpected semantic section content")

        if indent == 8:
            active_section_key = _parse_section_line(app, active_section, stripped, line_number)
            continue

        if indent >= 12 and active_section_key is not None:
            _append_section_detail(app, active_section, active_section_key, stripped)
            continue

        raise AxiomAppSyntaxError(f"Line {line_number}: unexpected indentation or section content")

    if app is None:
        raise AxiomAppSyntaxError("Missing app declaration")

    return app


def _indent_width(raw_line: str) -> int:
    if raw_line.startswith("\t"):
        raise AxiomAppSyntaxError("Tabs are not supported for indentation")
    return len(raw_line) - len(raw_line.lstrip(" "))


def _ensure_section(app: AppSpec, section: str) -> None:
    if section == "deploy":
        if app.deploy is None:
            app.deploy = DeploySpec()
        return

    if getattr(app, section) is None:
        setattr(app, section, AppComponent(name=section))


def _create_semantic_item(app: AppSpec, section: str, stripped: str, line_number: int) -> object:
    if not stripped.endswith(":"):
        raise AxiomAppSyntaxError(f"Line {line_number}: expected named item ending with ':' inside {section}")

    name = stripped.removesuffix(":").strip()
    if not name:
        raise AxiomAppSyntaxError(f"Line {line_number}: missing item name inside {section}")

    if section == "entities":
        item = EntitySpec(name=name)
        app.entities.append(item)
        return item
    if section == "roles":
        item = RoleSpec(name=name)
        app.roles.append(item)
        return item
    if section == "permissions":
        item = PermissionSpec(name=name)
        app.permissions.append(item)
        return item
    if section == "pages":
        item = PageSpec(name=name)
        app.pages.append(item)
        return item
    if section == "forms":
        item = FormSpec(name=name)
        app.forms.append(item)
        return item
    if section == "actions":
        item = ActionSpec(name=name)
        app.app_actions.append(item)
        return item
    if section == "workflows":
        item = WorkflowSpec(name=name)
        app.workflows.append(item)
        return item
    if section == "validations":
        item = ValidationSpec(name=name, rule="")
        app.validations.append(item)
        return item
    if section == "integrations":
        item = IntegrationSpec(name=name)
        app.integrations.append(item)
        return item
    if section == "jobs":
        item = JobSpec(name=name)
        app.jobs.append(item)
        return item
    if section == "events":
        item = EventSpec(name=name)
        app.events.append(item)
        return item

    raise AxiomAppSyntaxError(f"Line {line_number}: unsupported semantic section: {section}")


def _parse_semantic_item_line(section: str, item: object, stripped: str, line_number: int) -> str:
    if ":" not in stripped:
        raise AxiomAppSyntaxError(f"Line {line_number}: expected key: value or key:")

    key, value = (part.strip() for part in stripped.split(":", 1))
    if not key:
        raise AxiomAppSyntaxError(f"Line {line_number}: missing semantic key")

    normalized_key = _normalize_text_key(key)
    _set_semantic_value(section, item, normalized_key, value)
    return normalized_key


def _set_semantic_value(section: str, item: object, key: str, value: str) -> None:
    if isinstance(item, EntitySpec):
        if key in {"purpose", "descriptions"} and value:
            item.purpose.append(value)
        elif key == "validations" and value:
            item.validations.append(value)
        return

    if isinstance(item, RoleSpec):
        if key == "permissions" and value:
            item.permissions.append(value)
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, PermissionSpec):
        if key == "allows" and value:
            item.allows.append(value)
        elif key == "denies" and value:
            item.denies.append(value)
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, PageSpec):
        if key == "route":
            item.route = value or None
        elif key == "purpose" and value:
            item.purpose.append(value)
        elif key == "forms" and value:
            item.forms.append(value)
        elif key == "actions" and value:
            item.actions.append(value)
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, FormSpec):
        if key == "entity":
            item.entity = value or None
        elif key == "submit_action":
            item.submit_action = value or None
        elif key == "validations" and value:
            item.validations.append(value)
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, ActionSpec):
        if key == "actor":
            item.actor = value or None
        elif key == "purpose" and value:
            item.purpose.append(value)
        elif key == "inputs" and value:
            item.inputs.append(value)
        elif key == "outputs" and value:
            item.outputs.append(value)
        elif key == "effects" and value:
            item.effects.append(value)
        elif key == "errors" and value:
            item.errors.append(value)
        elif key == "validations" and value:
            item.validations.append(value)
        return

    if isinstance(item, WorkflowSpec):
        if key == "trigger":
            item.trigger = value or None
        elif key == "examples" and value:
            item.examples.append(value)
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, ValidationSpec):
        if key == "rule":
            item.rule = value
        elif key == "message":
            item.message = value or None
        elif key == "applies_to" and value:
            item.applies_to.append(value)
        return

    if isinstance(item, IntegrationSpec):
        if key == "provider":
            item.provider = value or None
        elif key == "capabilities" and value:
            item.capabilities.append(value)
        elif key == "credentials" and value:
            item.credentials.append(value)
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, JobSpec):
        if key == "schedule":
            item.schedule = value or None
        elif key == "action":
            item.action = value or None
        elif key == "descriptions" and value:
            item.descriptions.append(value)
        return

    if isinstance(item, EventSpec) and key == "descriptions" and value:
        item.descriptions.append(value)


def _append_semantic_item_detail(section: str, item: object, key: str, value: str) -> None:
    if isinstance(item, EntitySpec):
        if key in {"purpose", "descriptions"}:
            item.purpose.append(value)
        elif key == "fields":
            item.fields.append(_parse_field(value))
        elif key == "relationships":
            item.relationships.append(_parse_relationship(value))
        elif key == "validations":
            item.validations.append(value)
        return

    if isinstance(item, RoleSpec):
        if key == "permissions":
            item.permissions.append(value)
        elif key == "descriptions":
            item.descriptions.append(value)
        return

    if isinstance(item, PermissionSpec):
        if key == "allows":
            item.allows.append(value)
        elif key == "denies":
            item.denies.append(value)
        elif key == "descriptions":
            item.descriptions.append(value)
        return

    if isinstance(item, PageSpec):
        if key == "purpose":
            item.purpose.append(value)
        elif key == "forms":
            item.forms.append(value)
        elif key == "actions":
            item.actions.append(value)
        elif key == "descriptions":
            item.descriptions.append(value)
        return

    if isinstance(item, FormSpec):
        if key == "fields":
            item.fields.append(_parse_form_field(value))
        elif key == "validations":
            item.validations.append(value)
        elif key == "descriptions":
            item.descriptions.append(value)
        return

    if isinstance(item, ActionSpec):
        if key == "purpose":
            item.purpose.append(value)
        elif key == "inputs":
            item.inputs.append(value)
        elif key == "outputs":
            item.outputs.append(value)
        elif key == "effects":
            item.effects.append(value)
        elif key == "errors":
            item.errors.append(value)
        elif key == "validations":
            item.validations.append(value)
        return

    if isinstance(item, WorkflowSpec):
        if key == "steps":
            item.steps.append(_parse_workflow_step(value))
        elif key == "examples":
            item.examples.append(value)
        elif key == "descriptions":
            item.descriptions.append(value)
        return

    if isinstance(item, ValidationSpec):
        if key == "applies_to":
            item.applies_to.append(value)
        return

    if isinstance(item, IntegrationSpec):
        if key == "capabilities":
            item.capabilities.append(value)
        elif key == "credentials":
            item.credentials.append(value)
        elif key == "descriptions":
            item.descriptions.append(value)
        return

    if isinstance(item, EventSpec):
        if key == "payload":
            item.payload.append(_parse_field(value))
        elif key == "descriptions":
            item.descriptions.append(value)


def _parse_field(value: str) -> FieldSpec:
    name, raw_type = _split_named_value(value)
    parts = raw_type.split()
    type_name = parts[0] if parts else "Text"
    required = "optional" not in parts
    unique = "unique" in parts
    default = None
    if "default" in parts:
        default_index = parts.index("default")
        default = " ".join(parts[default_index + 1 :]) or None
    return FieldSpec(name=name, type_name=type_name, required=required, unique=unique, default=default)


def _parse_relationship(value: str) -> RelationshipSpec:
    name, raw_value = _split_named_value(value)
    parts = raw_value.split()
    target = parts[0] if parts else ""
    kind = " ".join(parts[1:]) or "related"
    return RelationshipSpec(name=name, target=target, kind=kind)


def _parse_form_field(value: str) -> FormFieldSpec:
    if ":" not in value:
        return FormFieldSpec(name=value)
    name, source = _split_named_value(value)
    return FormFieldSpec(name=name, source=source or None)


def _parse_workflow_step(value: str) -> WorkflowStepSpec:
    if ":" not in value:
        return WorkflowStepSpec(name=value)
    name, action = _split_named_value(value)
    return WorkflowStepSpec(name=name, action=action or None)


def _split_named_value(value: str) -> tuple[str, str]:
    name, raw_value = (part.strip() for part in value.split(":", 1))
    return name, raw_value


def _parse_section_line(app: AppSpec, section: str, stripped: str, line_number: int) -> str:
    if ":" not in stripped:
        if section == "deploy" and app.deploy is not None and app.deploy.target is None:
            app.deploy.target = stripped
            return "target"
        raise AxiomAppSyntaxError(f"Line {line_number}: expected key: value or key:")

    key, value = (part.strip() for part in stripped.split(":", 1))
    if not key:
        raise AxiomAppSyntaxError(f"Line {line_number}: missing section key")

    if section == "deploy":
        deploy = app.deploy
        if deploy is None:
            raise AxiomAppSyntaxError(f"Line {line_number}: deploy section was not initialized")
        _set_deploy_value(deploy, key, value)
        return _normalize_text_key(key)

    component = getattr(app, section)
    if component is None:
        raise AxiomAppSyntaxError(f"Line {line_number}: component section was not initialized")
    _set_component_value(component, key, value)
    return _normalize_text_key(key)


def _set_component_value(component: AppComponent, key: str, value: str) -> None:
    normalized_key = _normalize_text_key(key)
    if key == "stack":
        component.stack = value or None
    elif normalized_key in COMPONENT_TEXT_KEYS:
        if value:
            component.descriptions.append(value)
    elif value:
        component.details.setdefault(key, []).append(value)
    else:
        component.details.setdefault(key, [])


def _set_deploy_value(deploy: DeploySpec, key: str, value: str) -> None:
    normalized_key = _normalize_text_key(key)
    if key in {"target", "stack"}:
        deploy.target = value or None
    elif key == "credentials":
        if value:
            deploy.credentials.append(value)
    elif normalized_key in COMPONENT_TEXT_KEYS:
        if value:
            deploy.descriptions.append(value)
    elif value:
        deploy.details.setdefault(key, []).append(value)
    else:
        deploy.details.setdefault(key, [])


def _append_section_detail(app: AppSpec, section: str, key: str, value: str) -> None:
    if section == "deploy":
        deploy = app.deploy
        if deploy is None:
            return
        if key == "credentials":
            deploy.credentials.append(value)
        elif key in COMPONENT_TEXT_KEYS:
            deploy.descriptions.append(value)
        else:
            deploy.details.setdefault(key, []).append(value)
        return

    component = getattr(app, section)
    if component is None:
        return

    if key in COMPONENT_TEXT_KEYS:
        component.descriptions.append(value)
    else:
        component.details.setdefault(key, []).append(value)


def _normalize_text_key(key: str) -> str:
    if key == "description":
        return "descriptions"
    return key
