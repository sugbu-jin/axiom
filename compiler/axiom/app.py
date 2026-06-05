from dataclasses import dataclass, field


@dataclass(slots=True)
class AppComponent:
    name: str
    stack: str | None = None
    descriptions: list[str] = field(default_factory=list)
    details: dict[str, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class DeploySpec:
    target: str | None = None
    descriptions: list[str] = field(default_factory=list)
    credentials: list[str] = field(default_factory=list)
    details: dict[str, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class AppSpec:
    name: str
    purpose: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    action: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    frontend: AppComponent | None = None
    backend: AppComponent | None = None
    database: AppComponent | None = None
    deploy: DeploySpec | None = None
