# Axiom Roadmap

## 0.1 Prototype

- Minimal parser
- Python transpiler
- CLI
- Example runner
- Basic docs
- Collaboration metadata checks
- Project scaffolding, build, and run commands
- One-command app generation from a `.ax` file
- Stack targets for `python-cli`, `static-site`, and `fastapi-react-sqlite`
- App-level syntax with optional frontend, backend, database, and deploy sections
- Semantic app model for entities, roles, permissions, pages, forms, actions, workflows, validations, integrations, jobs, and events
- Compiler pipeline skeleton for parsed sources, semantic apps, app plans, and stack plans
- `auto` stack inference with `build/axiom-stack-plan.json`
- Plugin-style stack generator registry
- App diagnostics for missing data models, unclear flows, auth assumptions, persistence rules, and deployment security clarity

## 0.2 Language expansion

- Generate real CRUD behavior from semantic `entities`, `forms`, `actions`, and `workflows`
- Endpoint syntax and generated API route plans
- Effects and errors as enforced action contracts
- Enforced `ensures`
- Better expression parser
- Agent policy parsing
- Multi-file project imports
- Additional stack targets such as `fastapi`, `fastapi-react`, and `nextjs`
- Secure secret provider references for deployment workflows
- Semantic model validation across references, such as form fields pointing to entity fields

## 0.3 Tooling

- Formatter
- Linter
- VS Code extension
- TypeScript transpiler
- OpenAPI generation
- Documentation site

## 0.4 Agent governance

- Agent permissions
- Safe edit zones
- Project-level manifest
- Review checklist generator
- Machine-readable contributor workflow

## 1.0

- Stable syntax
- Stable compiler API
- Standard library
- Package registry design
