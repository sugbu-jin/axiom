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
