```markdown
# 🤖 Copilot Instructions — Dev Agent

These directions guide GitHub Copilot Chat/Agent when writing or modifying code
in this **dev-agent** repository.
Follow them exactly; any PR not conforming will be rejected by CI.

Whenever you run asynchronous commands in the terminal (i.e. curl, python, etc.),
you must output to a file, like `output.txt`, and then read the file
to get the output. This is to ensure that the output is captured correctly
by Copilot and can be used in subsequent steps.


Also, you should be self-aware that you have a tendency to delete a line-break from the
beginning of the code block, when you edit a file.  This behavior is consistent.  We use
use `black` on autosave, which does some to mitigate this, but you should always add an
extra line-break at the beginning of the code block when you edit a file.
This is to ensure that the code is formatted correctly and does not cause any issues.
Extra line-breaks are acceptable, as black will keep them from being an issue.

> This file is a **Copilot-only** instruction set; it is not for human developers.

---

## 1. Core Mission

* Implement an **AutoGen-based** multi-agent system that:
  1. Runs the target project’s tests.
  2. Generates minimal unified-diff patches via a local LLM.
  3. Iterates until the tests pass.
  4. Commits / pushes fixes and (optionally) opens a PR.

Your code must evolve through **TDD** phases listed in `docs/PROJECT-OUTLINE.md`.

---

## 2. Development Workflow

| Step                       | Requirement                                        |
|----------------------------|----------------------------------------------------|
| **Failing Test First**     | Every feature begins by adding ≥1 failing test in `tests/`. |
| **GREEN Implementation**   | Write only the code needed to pass the new tests.  |
| **REFACTOR**               | Clean up, document, add type hints.                |
| **Branch Naming**          | `feat/<slug>` or `fix/<slug>`; auto patches use `dev-agent/fix-*`. |
| **Commit Message**         | `TDD: <short imperative>` (≤ 50 chars).            |
| **PR Review**              | Ensure CI passes and no Copilot review comments remain. |

---

## 3. Code Style

* **Formatter**: run `black .` on save.
* **Import Sorter**: run `isort .` on save.
* **Lint**: satisfy `flake8` (via `ruff` later) with no warnings.
* **Typing**: add `mypy --strict`-compliant annotations in new code.
* **Docstrings**: Google style, first-sentence summary ≤72 chars.

Do **not** manually edit `__init__.py` files for import hygiene; rely on
`isort`.

---

## 4. Project Structure Conventions

```

agent\_lib/                 # Core modules
docs/                      # All design docs
tests/                     # Pytest suites + toy fixtures
scripts/                   # One-off utilities, no runtime deps

```

* Place **all runtime code** inside `agent_lib/` or the root `dev_agent.py`.
* Keep **test fixtures** under `tests/fixtures/…`, never in runtime paths.

---

## 5. Dependencies

* Add runtime deps only to **`requirements.txt`**.
* Add dev/test deps to **`requirements-dev.txt`**.
* Prefer stdlib over new packages; justify any heavies with a comment.
* For local-LLM backend use `llama-cpp-python` or `ollama`.

---

## 6. Pre-Commit Hooks

The repository’s `.pre-commit-config.yaml` will :

1. Run **black** + **isort**.
2. Run **flake8/ruff**.
3. Run **pytest** for the dev-agent’s own test suite.

Copilot must ensure hooks pass before proposing a commit.

---

## 7. Unit Test Guidelines

* Use **pytest** only—no `unittest`.
* Prefer **parametrized tests** for combinatorial cases.
* Keep tests **deterministic and offline** (mock LLM calls).
* Name tests verbosely: `test_<module>_<behavior>()`.

---

## 8. Security & Sandbox

* Shell commands must be white-listed (see `docs/AGENT-ARCHITECTURE.md`).
* Apply git patches with `git apply --check` before staging.
* Never execute external code fetched from the internet during tests.

---

## 9. Forbidden Patterns

* `eval` / `exec`
* Hard-coding absolute file paths
* Network calls in unit tests
* Non-UTF-8 source files

---

## 10. CI Expectations

CI runs:

1. `pre-commit run --all-files`
2. `pytest -q --cov=agent_lib`
3. Doc build check (`mkdocs build --strict`) once added

A PR is merge-ready **only** when CI passes **and** Supervisor role
(see `docs/AGENT-ARCHITECTURE.md`) replies with `approved: true`.

---

_Stick to these rules exactly; the automated Supervisor will reject
non-conforming contributions._
```
