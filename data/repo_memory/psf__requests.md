## Repository memory: psf/requests (AGENTS.md, frozen, repo-scoped)

### Module boundaries
- Top-level packages/modules: requests, test_requests.py
- Keep edits within the module that owns the behavior.

### Notes distilled from README.rst
- Browser-style SSL Verification
- Or, if you absolutely must:

### Common failure recovery
- If imports fail, check you are in the repo's env and the package is importable from the top-level package.
- If a test errors on collection, fix the import/signature before assuming the logic is wrong.
- Prefer minimal diffs; do not touch unrelated files or tests.
