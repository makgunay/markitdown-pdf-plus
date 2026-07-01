# Development workflow

The branch-to-merge cycle, commit conventions, the release process, and the dependency update policy.

## Environment

Development and tests run against the sibling venv `../markitdown/.venv` (which already has markitdown 0.1.6 and its dependencies). There is no venv committed in this repo. Install editable once:

```bash
../markitdown/.venv/bin/pip install -e ".[test,dev]"
```

Or use the reproducible dev container (Python 3.12 with all tooling, `pre-commit install` on create):

```bash
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . bash -lc "pytest -q"
```

## The cycle

1. **Branch** from `main`.
2. **Work test-first.** Add or adjust the targeted test for the stage you are changing, then make it pass. The git history is a sequence of small, focused commits (`feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `chore: ...`); match that style.
3. **Run the local gate** before committing:
   ```bash
   ../markitdown/.venv/bin/python -m pytest -q --cov --cov-report=term-missing
   ruff check src tests && ruff format --check src tests
   ../markitdown/.venv/bin/python -m mypy
   ```
4. **For table or heading changes**, also run the real-document eval (see [Testing](testing.md)).
5. **Commit.** `pre-commit` runs ruff, ruff-format, mypy, vulture, gitleaks, and the hygiene hooks; let it fix what it can and re-stage.
6. **Push and open a PR.** CI must be green. The PR template and CODEOWNERS apply (everything is owned by `@makgunay`).

## Keeping docs in sync

If you change the package's public surface, regenerate the API reference and verify the agent docs:

```bash
../markitdown/.venv/bin/python scripts/gen_api_docs.py          # regenerate docs/API.md
../markitdown/.venv/bin/python scripts/gen_api_docs.py --check  # CI fails if stale
../markitdown/.venv/bin/python scripts/validate_docs.py         # AGENTS.md/CLAUDE.md links + tools
```

`AGENTS.md` and `CLAUDE.md` are kept in sync intentionally: `CLAUDE.md` is the source of truth and `AGENTS.md` is the pointer. If you edit one, update the other.

## Releasing

Releases are cut by pushing a version tag:

```bash
git tag v0.2.0 && git push --tags
```

The `release` workflow (`.github/workflows/release.yml`) then builds the package, publishes to PyPI via Trusted Publishing (OIDC, no stored API token), and creates a GitHub release with auto-generated notes and the built artifacts attached. Update `CHANGELOG.md` and the version in `pyproject.toml` before tagging.

## Dependency update policy

Updates are automated via Dependabot (`.github/dependabot.yml`) for both pip and GitHub Actions, grouped and opened weekly. A minimum release age is enforced by Dependabot's `cooldown` setting: do not adopt a dependency bump until the target release is at least 7 days old (14 days for a major version). This guards against yanked, broken-on-release, or supply-chain-compromised versions that are pulled shortly after publication. Dependabot will not open the PR until the window has elapsed.
