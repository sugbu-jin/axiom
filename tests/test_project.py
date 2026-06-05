import tempfile
from pathlib import Path

from axiom.project import build_project, create_project, load_project, run_project


def test_create_project_scaffolds_axiom_app():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = create_project("todo-api", parent=tmpdir)

        assert root == Path(tmpdir) / "todo-api"
        assert (root / "axiom.toml").exists()
        assert (root / "src" / "main.ax").exists()
        assert 'entry = "todo_api.main"' in (root / "axiom.toml").read_text(encoding="utf-8")


def test_build_project_generates_python_entrypoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = create_project("todo-api", parent=tmpdir)
        outputs = build_project(root)

        output_names = {path.name for path in outputs}
        assert output_names == {"todo_api.py", "__main__.py"}
        assert "def main():" in (root / "build" / "todo_api.py").read_text(encoding="utf-8")


def test_run_project_executes_entrypoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = create_project("todo-api", parent=tmpdir)
        project = load_project(root)

        assert project.entry == "todo_api.main"
        assert run_project(root) == 0
