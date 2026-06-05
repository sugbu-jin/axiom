import re
from pathlib import Path

from .app import AppComponent, AppSpec, DeploySpec


IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
APP_RE = re.compile(rf"^app\s+(?P<name>{IDENTIFIER})\s*:$")
APP_TEXT_BLOCKS = {"purpose", "requires", "action", "examples"}
APP_SECTIONS = {"frontend", "backend", "database", "deploy"}
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
            continue

        if app is None:
            raise AxiomAppSyntaxError(f"Line {line_number}: app content before app declaration")

        if indent == 4:
            block_name = stripped.removesuffix(":")
            if stripped.endswith(":") and block_name in APP_TEXT_BLOCKS:
                active_app_block = block_name
                active_section = None
                active_section_key = None
                continue
            if stripped.endswith(":") and block_name in APP_SECTIONS:
                active_app_block = None
                active_section = block_name
                active_section_key = None
                _ensure_section(app, block_name)
                continue
            raise AxiomAppSyntaxError(f"Line {line_number}: unknown app block: {stripped}")

        if active_app_block is not None:
            if indent < 8:
                raise AxiomAppSyntaxError(f"Line {line_number}: expected content inside {active_app_block}")
            getattr(app, active_app_block).append(stripped)
            continue

        if active_section is None:
            raise AxiomAppSyntaxError(f"Line {line_number}: section content without an active section")

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
