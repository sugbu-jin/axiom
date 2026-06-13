from .base import StackGenerator
from .fastapi_react_sqlite import FastApiReactSqliteGenerator
from .python_cli import PythonCliGenerator
from .static_site import StaticSiteGenerator


_GENERATORS: dict[str, StackGenerator] = {
    generator.stack: generator
    for generator in [
        FastApiReactSqliteGenerator(),
        PythonCliGenerator(),
        StaticSiteGenerator(),
    ]
}


def get_generator(stack: str) -> StackGenerator | None:
    return _GENERATORS.get(stack)


def list_generator_stacks() -> list[str]:
    return sorted(_GENERATORS)
