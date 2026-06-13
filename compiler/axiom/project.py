import re
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from json import dumps
from pathlib import Path

from .app import AppComponent, AppSpec, DeploySpec
from .app_parser import is_app_source, parse_app_source
from .pipeline import parse_project_sources
from .transpiler_python import transpile_module


PROJECT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
ENTRYPOINT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$")
CONFIG_FILE = "axiom.toml"
DEFAULT_STACK = "python-cli"
SUPPORTED_STACKS = {"fastapi-react-sqlite", "python-cli", "static-site"}


class AxiomProjectError(Exception):
    """Raised when an Axiom project cannot be created, built, or run."""


@dataclass(frozen=True, slots=True)
class Project:
    root: Path
    name: str
    stack: str
    source: Path
    build: Path
    entry: str


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    root: Path
    outputs: list[Path]
    next_steps: list[str]


def create_project(name: str, parent: str | Path = ".", stack: str = DEFAULT_STACK) -> Path:
    if not PROJECT_NAME_RE.fullmatch(name):
        raise AxiomProjectError(
            "Project name must start with a letter and contain only letters, numbers, hyphens, or underscores."
        )
    if stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    root = Path(parent) / name
    if root.exists() and any(root.iterdir()):
        raise AxiomProjectError(f"Directory already exists and is not empty: {root}")

    module_name = _module_name_from_project(name)
    source_dir = root / "src"
    source_dir.mkdir(parents=True, exist_ok=True)

    (root / CONFIG_FILE).write_text(
        _project_config(name, stack, module_name),
        encoding="utf-8",
    )
    (source_dir / "main.ax").write_text(_starter_source(module_name, stack), encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(name, stack), encoding="utf-8")

    return root


def generate_project(source: str | Path, output: str | Path | None = None, stack: str = DEFAULT_STACK) -> GeneratedProject:
    source_path = Path(source)
    if not source_path.exists():
        raise AxiomProjectError(f"Source file does not exist: {source_path}")
    if source_path.suffix != ".ax":
        raise AxiomProjectError("Axiom source files must use the .ax extension")
    if stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    source_text = source_path.read_text(encoding="utf-8")
    project_name = _project_name_from_source(source_path, source_text)
    root = Path(output) if output is not None else Path(project_name)
    if root.exists() and any(root.iterdir()):
        raise AxiomProjectError(f"Output directory already exists and is not empty: {root}")

    root.mkdir(parents=True, exist_ok=True)
    module_name = _module_name_from_project(project_name)
    source_dir = root / "src"
    source_dir.mkdir(parents=True, exist_ok=True)

    (root / CONFIG_FILE).write_text(_project_config(project_name, stack, module_name), encoding="utf-8")
    (source_dir / "main.ax").write_text(source_text, encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(project_name, stack), encoding="utf-8")

    outputs = build_project(root)
    next_steps = _next_steps(root, stack)
    (root / "NEXT_STEPS.txt").write_text("\n".join(next_steps) + "\n", encoding="utf-8")

    return GeneratedProject(root=root, outputs=outputs, next_steps=next_steps)


def load_project(path: str | Path = ".") -> Project:
    root = Path(path).resolve()
    config_path = root / CONFIG_FILE
    if not config_path.exists():
        raise AxiomProjectError(f"Missing {CONFIG_FILE} in {root}")

    config = _read_config(config_path)
    name = config.get("name", root.name)
    stack = config.get("stack", DEFAULT_STACK)
    if stack not in SUPPORTED_STACKS:
        raise AxiomProjectError(_unsupported_stack_message(stack))

    source = root / config.get("source", "src")
    build = root / config.get("build", "build")
    entry = config.get("entry", f"{_module_name_from_project(name)}.main")

    return Project(root=root, name=name, stack=stack, source=source, build=build, entry=entry)


def build_project(path: str | Path = ".") -> list[Path]:
    project = load_project(path)
    if not project.source.exists():
        raise AxiomProjectError(f"Missing source directory: {project.source}")

    source_files = sorted(project.source.rglob("*.ax"))
    if not source_files:
        raise AxiomProjectError(f"No .ax source files found in {project.source}")

    project.build.mkdir(parents=True, exist_ok=True)
    parsed_project = parse_project_sources(source_files)
    apps = parsed_project.apps
    modules = parsed_project.modules

    if project.stack == "python-cli":
        return _build_python_cli(project, modules, apps)
    if project.stack == "static-site":
        return _build_static_site(project, modules, apps)
    if project.stack == "fastapi-react-sqlite":
        return _build_fastapi_react_sqlite(project, apps)

    raise AxiomProjectError(_unsupported_stack_message(project.stack))


def _build_python_cli(project: Project, modules: list, apps: list[AppSpec]) -> list[Path]:
    outputs: list[Path] = []

    for module in modules:
        output_path = project.build / f"{module.name}.py"
        output_path.write_text(transpile_module(module), encoding="utf-8")
        outputs.append(output_path)

    for index, app in enumerate(apps):
        module_name = _entry_module(project.entry) if index == 0 else _module_name_from_project(app.name)
        output_path = project.build / f"{module_name}.py"
        output_path.write_text(_app_python_code(app), encoding="utf-8")
        outputs.append(output_path)

    main_path = project.build / "__main__.py"
    main_path.write_text(_entrypoint_code(project.entry), encoding="utf-8")
    outputs.append(main_path)

    return outputs


def run_project(path: str | Path = ".") -> int:
    project = load_project(path)
    build_project(project.root)

    if project.stack == "static-site":
        index_path = project.build / "index.html"
        print(f"Static site built at {index_path}")
        return 0
    if project.stack == "fastapi-react-sqlite":
        print(f"Full-stack app generated at {project.build}")
        print("Backend:  cd build/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload")
        print("Frontend: cd build/frontend && npm install && npm run dev")
        return 0

    result = subprocess.run([sys.executable, "__main__.py"], cwd=project.build, text=True)
    return result.returncode


def list_stacks() -> list[str]:
    return sorted(SUPPORTED_STACKS)


def _next_steps(root: Path, stack: str) -> list[str]:
    lines = [
        f"Your Axiom app was generated at: {root}",
        "",
        "What to do next:",
    ]

    if stack == "fastapi-react-sqlite":
        lines.extend(
            [
                "1. Start the backend:",
                "   cd build/backend",
                "   python3 -m venv .venv",
                "   source .venv/bin/activate",
                "   pip install -r requirements.txt",
                "   uvicorn main:app --reload",
                "",
                "2. In a second terminal, start the frontend:",
                "   cd build/frontend",
                "   npm install",
                "   npm run dev",
                "",
                "3. Sign in with the demo account:",
                "   email: demo@example.com",
                "   password: password",
            ]
        )
    elif stack == "static-site":
        lines.extend(
            [
                "1. Open this file in your browser:",
                "   build/index.html",
            ]
        )
    else:
        lines.extend(
            [
                "1. Run the generated app:",
                "   axiom run",
            ]
        )

    return lines


def _read_config(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise AxiomProjectError(f"{path}:{line_number}: expected key = \"value\"")

        key, value = (part.strip() for part in line.split("=", 1))
        if not key:
            raise AxiomProjectError(f"{path}:{line_number}: missing config key")
        if len(value) < 2 or value[0] != '"' or value[-1] != '"':
            raise AxiomProjectError(f"{path}:{line_number}: config values must be quoted strings")

        config[key] = value[1:-1]

    return config


def _project_config(name: str, stack: str, module_name: str) -> str:
    return "\n".join(
        [
            f'name = "{name}"',
            f'stack = "{stack}"',
            'source = "src"',
            'build = "build"',
            f'entry = "{module_name}.main"',
            "",
        ]
    )


def _project_name_from_source(source_path: Path, source_text: str) -> str:
    if is_app_source(source_text):
        app = parse_app_source(source_text)
        return _slug_from_name(app.name)
    return _slug_from_name(source_path.stem)


def _slug_from_name(name: str) -> str:
    words = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)", name.replace("_", " ").replace("-", " "))
    slug = "-".join(word.lower() for word in words if word)
    return slug or "axiom-app"


def _module_name_from_project(name: str) -> str:
    return name.replace("-", "_")


def _entrypoint_code(entry: str) -> str:
    if not ENTRYPOINT_RE.fullmatch(entry):
        raise AxiomProjectError("Project entry must use module.function format")

    module_name, function_name = entry.rsplit(".", 1)
    return "\n".join(
        [
            f"from {module_name} import {function_name}",
            "",
            "",
            "if __name__ == '__main__':",
            f"    result = {function_name}()",
            "    raise SystemExit(result if isinstance(result, int) else 0)",
            "",
        ]
    )


def _build_static_site(project: Project, modules: list, apps: list[AppSpec]) -> list[Path]:
    index_path = project.build / "index.html"
    index_path.write_text(_static_site_html(project, modules, apps), encoding="utf-8")
    return [index_path]


def _build_fastapi_react_sqlite(project: Project, apps: list[AppSpec]) -> list[Path]:
    app = _first_app(apps)
    backend_dir = project.build / "backend"
    frontend_dir = project.build / "frontend"
    frontend_src_dir = frontend_dir / "src"

    backend_dir.mkdir(parents=True, exist_ok=True)
    frontend_src_dir.mkdir(parents=True, exist_ok=True)

    outputs = [
        backend_dir / "main.py",
        backend_dir / "requirements.txt",
        frontend_dir / "package.json",
        frontend_dir / "index.html",
        frontend_src_dir / "main.jsx",
        frontend_src_dir / "App.jsx",
        frontend_src_dir / "styles.css",
        project.build / "README.md",
    ]

    outputs[0].write_text(_fastapi_backend_code(app), encoding="utf-8")
    outputs[1].write_text("fastapi>=0.115.0\nuvicorn>=0.30.0\npydantic>=2.0.0\n", encoding="utf-8")
    outputs[2].write_text(_react_package_json(project.name), encoding="utf-8")
    outputs[3].write_text(_react_index_html(app), encoding="utf-8")
    outputs[4].write_text(_react_main_jsx(), encoding="utf-8")
    outputs[5].write_text(_react_app_jsx(app), encoding="utf-8")
    outputs[6].write_text(_react_styles_css(), encoding="utf-8")
    outputs[7].write_text(_full_stack_readme(project, app), encoding="utf-8")

    return outputs


def _app_python_code(app: AppSpec) -> str:
    lines = [
        f'"""Generated Axiom app: {app.name}."""',
        "",
        "",
        "def main():",
        f"    print({('Axiom app: ' + app.name)!r})",
    ]

    for purpose in app.purpose:
        lines.append(f"    print({('Purpose: ' + purpose)!r})")
    for requirement in app.requires:
        lines.append(f"    print({('Requirement: ' + requirement)!r})")
    for action in app.action:
        lines.append(f"    print({('Action: ' + action)!r})")

    for component in _iter_components(app):
        stack = component.stack or "not specified"
        lines.append(f"    print({(component.name.title() + ' stack: ' + stack)!r})")
        for description in component.descriptions:
            lines.append(f"    print({('  - ' + description)!r})")

    if app.deploy is not None:
        target = app.deploy.target or "not specified"
        lines.append(f"    print({('Deploy target: ' + target)!r})")
        if app.deploy.credentials:
            lines.append("    print('Deploy credentials: configured outside generated code')")

    lines.extend(["    return 0", ""])
    return "\n".join(lines)


def _static_site_html(project: Project, modules: list, apps: list[AppSpec]) -> str:
    sections: list[str] = []

    for app in apps:
        sections.append(_app_html(app))

    for module in modules:
        for function in module.functions:
            purpose = " ".join(function.purpose) if function.purpose else "No purpose provided."
            examples = "".join(f"<li><code>{escape(example)}</code></li>" for example in function.examples)
            if not examples:
                examples = "<li>No examples provided.</li>"
            sections.append(
                "\n".join(
                    [
                        '<section class="card">',
                        f"<h2>{escape(function.name)}</h2>",
                        f"<p>{escape(purpose)}</p>",
                        "<h3>Examples</h3>",
                        f"<ul>{examples}</ul>",
                        "</section>",
                    ]
                )
            )

    content = "\n".join(sections) or '<section class="card"><p>No Axiom functions found.</p></section>'

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escape(project.name)}</title>",
            "  <style>",
            "    body { font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; color: #0f172a; }",
            "    main { max-width: 760px; margin: 0 auto; }",
            "    .card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin: 1rem 0; }",
            "    code { background: #f1f5f9; padding: 0.1rem 0.3rem; border-radius: 4px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <main>",
            f"    <h1>{escape(project.name)}</h1>",
            "    <p>Generated by Axiom using the static-site stack.</p>",
            content,
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _app_html(app: AppSpec) -> str:
    parts = [
        '<section class="card">',
        f"<h2>{escape(app.name)}</h2>",
        _paragraph_list("Purpose", app.purpose),
        _paragraph_list("Requirements", app.requires),
        _paragraph_list("Actions", app.action),
        _paragraph_list("Examples", app.examples),
    ]

    for component in _iter_components(app):
        parts.append(_component_html(component))

    if app.deploy is not None:
        parts.append(_deploy_html(app.deploy))

    parts.append("</section>")
    return "\n".join(parts)


def _component_html(component: AppComponent) -> str:
    stack = escape(component.stack or "not specified")
    return "\n".join(
        [
            f"<h3>{escape(component.name.title())}</h3>",
            f"<p><strong>Stack:</strong> {stack}</p>",
            _paragraph_list("Description", component.descriptions),
        ]
    )


def _deploy_html(deploy: DeploySpec) -> str:
    target = escape(deploy.target or "not specified")
    credential_note = ""
    if deploy.credentials:
        credential_note = "<p><strong>Credentials:</strong> configured outside generated code</p>"
    return "\n".join(
        [
            "<h3>Deploy</h3>",
            f"<p><strong>Target:</strong> {target}</p>",
            _paragraph_list("Description", deploy.descriptions),
            credential_note,
        ]
    )


def _paragraph_list(title: str, items: list[str]) -> str:
    if not items:
        return ""
    rendered = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<h3>{escape(title)}</h3><ul>{rendered}</ul>"


def _iter_components(app: AppSpec) -> list[AppComponent]:
    return [component for component in [app.frontend, app.backend, app.database] if component is not None]


def _entry_module(entry: str) -> str:
    return entry.rsplit(".", 1)[0]


def _starter_source(module_name: str, stack: str) -> str:
    app_name = _app_name_from_module(module_name)
    if stack == "fastapi-react-sqlite":
        return _starter_login_source(app_name)
    if stack == "static-site":
        purpose = "Describe the main page of the generated site."
        frontend_stack = "static-site"
    else:
        purpose = "Start the application."
        frontend_stack = "terminal"

    return "\n".join(
        [
            f"app {app_name}:",
            "",
            "    purpose:",
            f"        {purpose}",
            "",
            "    requires:",
            "        The app should be simple to understand and safe to change.",
            "",
            "    action:",
            "        Show a friendly starter experience.",
            "",
            "    examples:",
            "        When the app runs, people can see it was generated by Axiom.",
            "",
            "    frontend:",
            f"        stack: {frontend_stack}",
            "        descriptions:",
            "            Present the starter experience clearly.",
            "",
            "    backend:",
            "        stack: none",
            "        descriptions:",
            "            No backend is required for the starter app.",
            "",
        ]
    )


def _starter_readme(name: str, stack: str) -> str:
    return "\n".join(
        [
            f"# {name}",
            "",
            f"Generated by Axiom using the `{stack}` stack.",
            "",
            "## Commands",
            "",
            "```bash",
            "axiom build",
            "axiom run",
            "```",
            "",
        ]
    )


def _unsupported_stack_message(stack: str) -> str:
    supported = ", ".join(list_stacks())
    return f"Unsupported stack {stack!r}. Supported stacks: {supported}"


def _app_name_from_module(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))


def _first_app(apps: list[AppSpec]) -> AppSpec:
    if not apps:
        raise AxiomProjectError("The fastapi-react-sqlite stack requires an app declaration.")
    return apps[0]


def _fastapi_backend_code(app: AppSpec) -> str:
    title = f"{app.name} API"
    return "\n".join(
        [
            "from datetime import datetime, timezone",
            "import hashlib",
            "import hmac",
            "import os",
            "import secrets",
            "import sqlite3",
            "from pathlib import Path",
            "",
            "from fastapi import FastAPI, HTTPException",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from pydantic import BaseModel",
            "",
            "",
            f"app = FastAPI(title={title!r})",
            "app.add_middleware(",
            "    CORSMiddleware,",
            "    allow_origins=[os.getenv('AXIOM_FRONTEND_ORIGIN', 'http://localhost:5173')],",
            "    allow_credentials=True,",
            "    allow_methods=['*'],",
            "    allow_headers=['*'],",
            ")",
            "",
            "DB_PATH = Path(os.getenv('AXIOM_DB_PATH', 'app.db'))",
            "PASSWORD_ITERATIONS = 120_000",
            "",
            "",
            "class LoginRequest(BaseModel):",
            "    email: str",
            "    password: str",
            "",
            "",
            "def get_connection():",
            "    connection = sqlite3.connect(DB_PATH)",
            "    connection.row_factory = sqlite3.Row",
            "    return connection",
            "",
            "",
            "def hash_password(password: str, salt: bytes | None = None) -> str:",
            "    if salt is None:",
            "        salt = secrets.token_bytes(16)",
            "    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_ITERATIONS)",
            "    return f'{salt.hex()}:{digest.hex()}'",
            "",
            "",
            "def verify_password(password: str, stored_hash: str) -> bool:",
            "    try:",
            "        salt_hex, digest_hex = stored_hash.split(':', 1)",
            "        expected = hash_password(password, bytes.fromhex(salt_hex)).split(':', 1)[1]",
            "    except ValueError:",
            "        return False",
            "    return hmac.compare_digest(expected, digest_hex)",
            "",
            "",
            "def init_db():",
            "    with get_connection() as connection:",
            "        connection.execute(",
            "            '''",
            "            CREATE TABLE IF NOT EXISTS users (",
            "                id INTEGER PRIMARY KEY AUTOINCREMENT,",
            "                email TEXT NOT NULL UNIQUE,",
            "                password_hash TEXT NOT NULL,",
            "                created_at TEXT NOT NULL",
            "            )",
            "            '''",
            "        )",
            "        demo_email = os.getenv('AXIOM_DEMO_EMAIL', 'demo@example.com')",
            "        demo_password = os.getenv('AXIOM_DEMO_PASSWORD', 'password')",
            "        existing = connection.execute('SELECT id FROM users WHERE email = ?', (demo_email,)).fetchone()",
            "        if existing is None:",
            "            connection.execute(",
            "                'INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)',",
            "                (demo_email, hash_password(demo_password), datetime.now(timezone.utc).isoformat()),",
            "            )",
            "",
            "",
            "init_db()",
            "",
            "",
            "@app.get('/api/health')",
            "def health():",
            "    return {'status': 'ok'}",
            "",
            "",
            "@app.post('/api/login')",
            "def login(payload: LoginRequest):",
            "    email = payload.email.strip().lower()",
            "    if not email or not payload.password:",
            "        raise HTTPException(status_code=400, detail='Email and password are required.')",
            "",
            "    with get_connection() as connection:",
            "        user = connection.execute('SELECT id, email, password_hash FROM users WHERE email = ?', (email,)).fetchone()",
            "",
            "    if user is None or not verify_password(payload.password, user['password_hash']):",
            "        raise HTTPException(status_code=401, detail='Invalid email or password.')",
            "",
            "    return {",
            "        'message': 'Login successful.',",
            "        'token': secrets.token_urlsafe(24),",
            "        'user': {'id': user['id'], 'email': user['email']},",
            "    }",
            "",
        ]
    )


def _react_package_json(project_name: str) -> str:
    return dumps(
        {
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"@vitejs/plugin-react": "latest", "vite": "latest", "react": "latest", "react-dom": "latest"},
            "devDependencies": {},
            "private": True,
            "name": _module_name_from_project(project_name),
            "version": "0.1.0",
        },
        indent=2,
    ) + "\n"


def _react_index_html(app: AppSpec) -> str:
    return "\n".join(
        [
            '<!doctype html>',
            '<html lang="en">',
            '  <head>',
            '    <meta charset="UTF-8" />',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
            f'    <title>{escape(app.name)}</title>',
            '  </head>',
            '  <body>',
            '    <div id="root"></div>',
            '    <script type="module" src="/src/main.jsx"></script>',
            '  </body>',
            '</html>',
            '',
        ]
    )


def _react_main_jsx() -> str:
    return "\n".join(
        [
            "import React from 'react';",
            "import { createRoot } from 'react-dom/client';",
            "import App from './App.jsx';",
            "import './styles.css';",
            "",
            "createRoot(document.getElementById('root')).render(",
            "  <React.StrictMode>",
            "    <App />",
            "  </React.StrictMode>,",
            ");",
            "",
        ]
    )


def _react_app_jsx(app: AppSpec) -> str:
    purpose = " ".join(app.purpose) or "Sign in to continue."
    requirements = app.requires or ["Enter an email and password."]
    return "\n".join(
        [
            "import { useState } from 'react';",
            "",
            "const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';",
            f"const PURPOSE = {purpose!r};",
            f"const REQUIREMENTS = {dumps(requirements)};",
            "",
            "export default function App() {",
            "  const [email, setEmail] = useState('demo@example.com');",
            "  const [password, setPassword] = useState('password');",
            "  const [message, setMessage] = useState('');",
            "  const [error, setError] = useState('');",
            "  const [loading, setLoading] = useState(false);",
            "",
            "  async function handleSubmit(event) {",
            "    event.preventDefault();",
            "    setError('');",
            "    setMessage('');",
            "    setLoading(true);",
            "",
            "    try {",
            "      const response = await fetch(`${API_BASE}/api/login`, {",
            "        method: 'POST',",
            "        headers: { 'Content-Type': 'application/json' },",
            "        body: JSON.stringify({ email, password }),",
            "      });",
            "      const data = await response.json();",
            "      if (!response.ok) {",
            "        throw new Error(data.detail || 'Login failed.');",
            "      }",
            "      setMessage(`${data.message} Welcome, ${data.user.email}.`);",
            "    } catch (err) {",
            "      setError(err.message);",
            "    } finally {",
            "      setLoading(false);",
            "    }",
            "  }",
            "",
            "  return (",
            "    <main className=\"page\">",
            "      <section className=\"card\">",
            f"        <p className=\"eyebrow\">Generated by Axiom</p>",
            f"        <h1>{escape(app.name)}</h1>",
            "        <p>{PURPOSE}</p>",
            "",
            "        <form onSubmit={handleSubmit}>",
            "          <label>",
            "            Email",
            "            <input value={email} onChange={(event) => setEmail(event.target.value)} type=\"email\" required />",
            "          </label>",
            "          <label>",
            "            Password",
            "            <input value={password} onChange={(event) => setPassword(event.target.value)} type=\"password\" required />",
            "          </label>",
            "          <button disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>",
            "        </form>",
            "",
            "        {message && <p className=\"success\">{message}</p>}",
            "        {error && <p className=\"error\">{error}</p>}",
            "      </section>",
            "",
            "      <section className=\"notes\">",
            "        <h2>Requirements</h2>",
            "        <ul>",
            "          {REQUIREMENTS.map((item) => <li key={item}>{item}</li>)}",
            "        </ul>",
            "      </section>",
            "    </main>",
            "  );",
            "}",
            "",
        ]
    )


def _react_styles_css() -> str:
    return "\n".join(
        [
            ":root { font-family: Inter, system-ui, sans-serif; color: #0f172a; background: #f8fafc; }",
            "body { margin: 0; }",
            ".page { min-height: 100vh; display: grid; place-items: center; gap: 1rem; padding: 2rem; }",
            ".card, .notes { width: min(100%, 440px); background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 1.5rem; box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08); }",
            ".eyebrow { color: #2563eb; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }",
            "form { display: grid; gap: 1rem; margin-top: 1rem; }",
            "label { display: grid; gap: 0.4rem; font-weight: 600; }",
            "input { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.75rem; font: inherit; }",
            "button { border: 0; border-radius: 10px; padding: 0.85rem; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }",
            "button:disabled { opacity: 0.65; cursor: wait; }",
            ".success { color: #047857; font-weight: 700; }",
            ".error { color: #b91c1c; font-weight: 700; }",
            ".notes { place-self: start center; }",
            "",
        ]
    )


def _full_stack_readme(project: Project, app: AppSpec) -> str:
    return "\n".join(
        [
            f"# {app.name}",
            "",
            "Generated by Axiom using the `fastapi-react-sqlite` stack.",
            "",
            "## Backend",
            "",
            "```bash",
            "cd backend",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
            "uvicorn main:app --reload",
            "```",
            "",
            "The backend seeds a demo user by default:",
            "",
            "```text",
            "email: demo@example.com",
            "password: password",
            "```",
            "",
            "Override these with `AXIOM_DEMO_EMAIL` and `AXIOM_DEMO_PASSWORD`.",
            "",
            "## Frontend",
            "",
            "```bash",
            "cd frontend",
            "npm install",
            "npm run dev",
            "```",
            "",
            "Set `VITE_API_BASE` if the backend is not running at `http://localhost:8000`.",
            "",
        ]
    )


def _starter_login_source(app_name: str) -> str:
    return "\n".join(
        [
            f"app {app_name}:",
            "    purpose:",
            "        Let users sign in securely before accessing a protected app.",
            "",
            "    requires:",
            "        Users can enter an email and password.",
            "        Passwords are never stored as plain text.",
            "        Failed login attempts show a clear error message.",
            "",
            "    action:",
            "        Create a login page connected to a SQLite-backed user store.",
            "",
            "    examples:",
            "        When a user enters a valid email and password, they reach the dashboard.",
            "",
            "    frontend:",
            "        stack: react",
            "        descriptions:",
            "            Show a centered login form with email and password fields.",
            "",
            "    backend:",
            "        stack: fastapi",
            "        descriptions:",
            "            Provide an endpoint for login requests.",
            "",
            "    database:",
            "        stack: sqlite",
            "        descriptions:",
            "            Store users with id, email, password_hash, and created_at fields.",
            "",
            "    deploy:",
            "        target: local",
            "        credentials:",
            "            env",
            "",
        ]
    )
