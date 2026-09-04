---
name: github-actions
description: "GitHub Actions CI for Python/FastAPI projects: lint, test, coverage, Docker build, security scans. Use for .github/workflows setup and debugging CI failures."
---

# GitHub Actions

## Recommended Workflows for this stack
- `ci.yml`: ruff, pytest with coverage, mypy/pyright, docker build (test).
- `security.yml`: pip-audit or safety, trivy for Docker, secret scanning.
- Matrix for Python 3.11+.

## Key Jobs
```yaml
- name: Test
  run: |
    pip install -e ".[dev]"
    ruff check .
    pytest -q --cov --cov-report=xml
- name: Docker
  uses: docker/build-push-action
  with:
    push: false
    tags: test:latest
```

## Debugging CI
- Reproduce locally with `act` (if installed) or exact same pytest command.
- Use `tdd-test-engineer` for flaky test reproduction.
- Check coverage upload to Codecov or similar.

See also `git-github-flow` and superpowers using-git-worktrees.
