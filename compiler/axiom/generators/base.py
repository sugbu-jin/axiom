from dataclasses import dataclass
from pathlib import Path

from axiom.app import AppSpec
from axiom.ast import Module


class AxiomGeneratorError(Exception):
    """Raised when a stack generator cannot produce output."""


@dataclass(frozen=True, slots=True)
class BuildContext:
    root: Path
    name: str
    build: Path
    entry: str


class StackGenerator:
    stack: str

    def build(self, context: BuildContext, modules: list[Module], apps: list[AppSpec]) -> list[Path]:
        raise NotImplementedError
