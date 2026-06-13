from axiom.generators import get_generator, list_generator_stacks


def test_generator_registry_exposes_supported_stack_plugins():
    assert list_generator_stacks() == ["fastapi-react-sqlite", "python-cli", "static-site"]
    assert get_generator("python-cli") is not None
    assert get_generator("static-site") is not None
    assert get_generator("fastapi-react-sqlite") is not None
    assert get_generator("unknown") is None
