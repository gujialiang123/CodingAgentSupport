## Repository memory: pylint-dev/pylint (AGENTS.md, frozen, repo-scoped)

### Module boundaries
- Top-level packages/modules: pylint, script
- Keep edits within the module that owns the behavior.

### Conventions & tooling
- Config/convention files: setup.cfg, tox.ini
- Repo configures `isort`; match its settings.
- Repo configures `mypy`; match its settings.
- Repo configures `pytest`; match its settings.
- Declared Python versions: 3.6, 3.7, 3.8, 3.9

### Fixture patterns
- Repo uses pytest `conftest.py` fixtures; reuse existing fixtures rather than constructing state inline.

### Common failure recovery
- If imports fail, check you are in the repo's env and the package is importable from the top-level package.
- If a test errors on collection, fix the import/signature before assuming the logic is wrong.
- Prefer minimal diffs; do not touch unrelated files or tests.
