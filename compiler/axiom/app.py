from dataclasses import dataclass, field


@dataclass(slots=True)
class FieldSpec:
    name: str
    type_name: str
    required: bool = True
    unique: bool = False
    default: str | None = None
    descriptions: list[str] = field(default_factory=list)
    validations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RelationshipSpec:
    name: str
    target: str
    kind: str
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EntitySpec:
    name: str
    purpose: list[str] = field(default_factory=list)
    fields: list[FieldSpec] = field(default_factory=list)
    relationships: list[RelationshipSpec] = field(default_factory=list)
    validations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PermissionSpec:
    name: str
    allows: list[str] = field(default_factory=list)
    denies: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RoleSpec:
    name: str
    permissions: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FormFieldSpec:
    name: str
    source: str | None = None
    required: bool = True
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FormSpec:
    name: str
    entity: str | None = None
    fields: list[FormFieldSpec] = field(default_factory=list)
    submit_action: str | None = None
    validations: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PageSpec:
    name: str
    route: str | None = None
    purpose: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ActionSpec:
    name: str
    purpose: list[str] = field(default_factory=list)
    actor: str | None = None
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowStepSpec:
    name: str
    action: str | None = None
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowSpec:
    name: str
    trigger: str | None = None
    steps: list[WorkflowStepSpec] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValidationSpec:
    name: str
    rule: str
    message: str | None = None
    applies_to: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IntegrationSpec:
    name: str
    provider: str | None = None
    capabilities: list[str] = field(default_factory=list)
    credentials: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class JobSpec:
    name: str
    schedule: str | None = None
    action: str | None = None
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EventSpec:
    name: str
    payload: list[FieldSpec] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


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
    entities: list[EntitySpec] = field(default_factory=list)
    roles: list[RoleSpec] = field(default_factory=list)
    permissions: list[PermissionSpec] = field(default_factory=list)
    pages: list[PageSpec] = field(default_factory=list)
    forms: list[FormSpec] = field(default_factory=list)
    app_actions: list[ActionSpec] = field(default_factory=list)
    workflows: list[WorkflowSpec] = field(default_factory=list)
    validations: list[ValidationSpec] = field(default_factory=list)
    integrations: list[IntegrationSpec] = field(default_factory=list)
    jobs: list[JobSpec] = field(default_factory=list)
    events: list[EventSpec] = field(default_factory=list)
    frontend: AppComponent | None = None
    backend: AppComponent | None = None
    database: AppComponent | None = None
    deploy: DeploySpec | None = None
