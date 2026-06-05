from dataclasses import dataclass, field


@dataclass(slots=True)
class Parameter:
    name: str
    type_name: str


@dataclass(slots=True)
class FunctionDef:
    name: str
    parameters: list[Parameter]
    return_type: str
    purpose: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    ensures: list[str] = field(default_factory=list)
    action: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Module:
    name: str
    functions: list[FunctionDef] = field(default_factory=list)
