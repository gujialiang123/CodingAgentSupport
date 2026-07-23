## Repository memory: pydata/xarray (AGENTS.md, frozen, repo-scoped)

### Module boundaries
- Top-level packages/modules: conftest.py, versioneer.py, xarray
- Keep edits within the module that owns the behavior.

### Conventions & tooling
- Config/convention files: setup.cfg
- Repo configures `flake8`; match its settings.
- Repo configures `black`; match its settings.
- Repo configures `isort`; match its settings.
- Repo configures `mypy`; match its settings.
- Repo configures `pytest`; match its settings.

### Fixture patterns
- Repo uses pytest `conftest.py` fixtures; reuse existing fixtures rather than constructing state inline.

### Common failure recovery
- If imports fail, check you are in the repo's env and the package is importable from the top-level package.
- If a test errors on collection, fix the import/signature before assuming the logic is wrong.
- Prefer minimal diffs; do not touch unrelated files or tests.
