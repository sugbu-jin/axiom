from html import escape
from json import dumps
from pathlib import Path

from axiom.app import AppSpec
from axiom.ast import Module

from .base import AxiomGeneratorError, BuildContext, StackGenerator


class FastApiReactSqliteGenerator(StackGenerator):
    stack = "fastapi-react-sqlite"

    def build(self, context: BuildContext, modules: list[Module], apps: list[AppSpec]) -> list[Path]:
        app = _first_app(apps)
        backend_dir = context.build / "backend"
        frontend_dir = context.build / "frontend"
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
            context.build / "README.md",
        ]

        outputs[0].write_text(_fastapi_backend_code(app), encoding="utf-8")
        outputs[1].write_text("fastapi>=0.115.0\nuvicorn>=0.30.0\npydantic>=2.0.0\n", encoding="utf-8")
        outputs[2].write_text(_react_package_json(context.name), encoding="utf-8")
        outputs[3].write_text(_react_index_html(app), encoding="utf-8")
        outputs[4].write_text(_react_main_jsx(), encoding="utf-8")
        outputs[5].write_text(_react_app_jsx(app), encoding="utf-8")
        outputs[6].write_text(_react_styles_css(), encoding="utf-8")
        outputs[7].write_text(_full_stack_readme(app), encoding="utf-8")

        return outputs


def _first_app(apps: list[AppSpec]) -> AppSpec:
    if not apps:
        raise AxiomGeneratorError("The fastapi-react-sqlite stack requires an app declaration.")
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


def _full_stack_readme(app: AppSpec) -> str:
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


def _module_name_from_project(name: str) -> str:
    return name.replace("-", "_")
