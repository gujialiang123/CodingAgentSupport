## Repository memory: pytest-dev/pytest (AGENTS.md, frozen, repo-scoped)

### Conventions & tooling
- Config/convention files: pyproject.toml, setup.cfg, tox.ini
- Repo configures `flake8`; match its settings.
- Repo configures `isort`; match its settings.
- Repo configures `pytest`; match its settings.
- Declared Python versions: 2.7, 3.4, 3.5, 3.6, 3.7

### Common failure recovery
- If imports fail, check you are in the repo's env and the package is importable from the top-level package.
- If a test errors on collection, fix the import/signature before assuming the logic is wrong.
- Prefer minimal diffs; do not touch unrelated files or tests.
