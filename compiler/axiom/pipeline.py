from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .app import AppSpec
from .app_parser import is_app_source, parse_app_source
from .ast import Module
from .parser import parse_file


SourceKind = Literal["app", "module"]


@dataclass(frozen=True, slots=True)
class ParsedSource:
    path: Path
    kind: SourceKind
    app: AppSpec | None = None
    module: Module | None = None


@dataclass(frozen=True, slots=True)
class ParsedProject:
    sources: list[ParsedSource] = field(default_factory=list)

    @property
    def apps(self) -> list[AppSpec]:
        return [source.app for source in self.sources if source.app is not None]

    @property
    def modules(self) -> list[Module]:
        return [source.module for source in self.sources if source.module is not None]


@dataclass(frozen=True, slots=True)
class SemanticApp:
    app: AppSpec
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AppPlan:
    semantic_app: SemanticApp
    stack: str
    generator: str


@dataclass(frozen=True, slots=True)
class StackPlan:
    requested_stack: str
    selected_stack: str
    inferred: bool
    capabilities: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def parse_axiom_source(path: str | Path) -> ParsedSource:
    source_path = Path(path)
    source = source_path.read_text(encoding="utf-8")

    if is_app_source(source):
        return ParsedSource(path=source_path, kind="app", app=parse_app_source(source))

    return ParsedSource(path=source_path, kind="module", module=parse_file(source_path))


def parse_project_sources(source_files: list[Path]) -> ParsedProject:
    return ParsedProject(sources=[parse_axiom_source(path) for path in sorted(source_files)])


def build_semantic_app(app: AppSpec) -> SemanticApp:
    return SemanticApp(app=app, capabilities=_detect_capabilities(app))


def build_app_plan(app: AppSpec, stack: str) -> AppPlan:
    return AppPlan(
        semantic_app=build_semantic_app(app),
        stack=stack,
        generator=stack,
    )


def build_app_plans(apps: list[AppSpec], stack: str) -> list[AppPlan]:
    return [build_app_plan(app, stack) for app in apps]


def infer_stack(parsed_project: ParsedProject, requested_stack: str) -> StackPlan:
    capabilities = _project_capabilities(parsed_project.apps)

    if requested_stack != "auto":
        return StackPlan(
            requested_stack=requested_stack,
            selected_stack=requested_stack,
            inferred=False,
            capabilities=capabilities,
            reasons=[f"Stack was explicitly configured as {requested_stack}."],
        )

    if not parsed_project.apps:
        return StackPlan(
            requested_stack=requested_stack,
            selected_stack="python-cli",
            inferred=True,
            capabilities=capabilities,
            reasons=["Only module/function sources were found, so a Python CLI build is the safest default."],
        )

    if _needs_full_stack_web_app(capabilities):
        return StackPlan(
            requested_stack=requested_stack,
            selected_stack="fastapi-react-sqlite",
            inferred=True,
            capabilities=capabilities,
            reasons=[
                "The app definition includes UI plus stateful application capabilities.",
                "React, FastAPI, and SQLite are the current supported full-stack target.",
            ],
        )

    if "user-interface" in capabilities:
        return StackPlan(
            requested_stack=requested_stack,
            selected_stack="static-site",
            inferred=True,
            capabilities=capabilities,
            reasons=["The app definition describes UI content without stateful backend requirements."],
        )

    return StackPlan(
        requested_stack=requested_stack,
        selected_stack="python-cli",
        inferred=True,
        capabilities=capabilities,
        reasons=["No UI or persistence requirements were found, so a Python CLI build is the safest default."],
    )


def _detect_capabilities(app: AppSpec) -> list[str]:
    capabilities: set[str] = set()

    if app.entities:
        capabilities.add("data-model")
    if app.pages or app.forms or app.frontend is not None:
        capabilities.add("user-interface")
    if app.app_actions or app.workflows:
        capabilities.add("workflow")
    if app.roles or app.permissions:
        capabilities.add("authorization")
    if app.database is not None or _has_persistence_effect(app):
        capabilities.add("persistence")
    if app.integrations:
        capabilities.add("integration")
    if app.jobs:
        capabilities.add("background-jobs")
    if app.events:
        capabilities.add("events")
    if app.deploy is not None:
        capabilities.add("deployment")

    return sorted(capabilities)


def _has_persistence_effect(app: AppSpec) -> bool:
    return any("persist" in effect.lower() or "store" in effect.lower() for action in app.app_actions for effect in action.effects)


def _project_capabilities(apps: list[AppSpec]) -> list[str]:
    capabilities: set[str] = set()
    for app in apps:
        capabilities.update(build_semantic_app(app).capabilities)
    return sorted(capabilities)


def _needs_full_stack_web_app(capabilities: list[str]) -> bool:
    stateful_capabilities = {
        "authorization",
        "background-jobs",
        "data-model",
        "events",
        "integration",
        "persistence",
        "workflow",
    }
    return "user-interface" in capabilities and any(capability in stateful_capabilities for capability in capabilities)
