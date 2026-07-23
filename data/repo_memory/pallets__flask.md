## Repository memory: pallets/flask (AGENTS.md, frozen, repo-scoped)

### Conventions & tooling
- Config/convention files: pyproject.toml, tox.ini
- Repo configures `mypy`; match its settings.
- Repo configures `pytest`; match its settings.

### Fixture patterns
- Repo uses pytest `conftest.py` fixtures; reuse existing fixtures rather than constructing state inline.

### Notes distilled from README.rst
- allow the maintainers to devote more time to the projects, `please

### Common failure recovery
- If imports fail, check you are in the repo's env and the package is importable from the top-level package.
- If a test errors on collection, fix the import/signature before assuming the logic is wrong.
- Prefer minimal diffs; do not touch unrelated files or tests.
