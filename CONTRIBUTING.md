# 👐 Contributing Guide — Dev Agent

Welcome! 🎉
This project relies on **strict Test-Driven Development** and automated review
by an LLM Supervisor.
Follow the steps below to ensure a smooth PR experience.

---

## 1. Getting Started

```bash
# Clone and set up pre-commit hooks
git clone https://github.com/<your-org>/dev-agent.git
cd dev-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
````

*All commits will now auto-run `black`, `isort`, `flake8`, and `pytest`.*

---

## 2. Branching & Naming

| Purpose       | Pattern                    | Example                       |
| ------------- | -------------------------- | ----------------------------- |
| Feature       | `feat/<slug>`              | `feat/test-runner-timeout`    |
| Bug fix       | `fix/<slug>`               | `fix/git-apply-windows-paths` |
| Docs only     | `docs/<slug>`              | `docs/update-readme`          |
| Auto patches† | `dev-agent/fix-<testname>` | `dev-agent/fix-test_addition` |

† *Branches starting with `dev-agent/` are created by the agent itself.*

---

## 3. Commit Style

* Single-purpose commits.
* Message format:

  ```
  TDD: <imperative summary>  (<= 50 chars)

  * optional bullet list
  * wraps at 72 chars
  ```
* Do **not** squash auto-generated commits unless you are the agent.

---

## 4. Writing Code

1. **RED** – add failing test(s) in `tests/`.
2. **GREEN** – minimal implementation in `agent_lib/` or `dev_agent.py`.
3. **REFACTOR** – cleanup, docstrings, type hints.
4. Ensure `mypy --strict` passes (CI will check).
5. Run `pre-commit run --all-files` locally before pushing.

---

## 5. Adding Dependencies

* **Runtime** → `requirements.txt` (explain in PR description).
* **Dev/Test** → `requirements-dev.txt`.
* Prefer stdlib; justify heavy libs.
* Update `requirements*.txt` with `pip-compile` (if installed).

---

## 6. Pull Request Checklist

* [ ] All new code is covered by tests.
* [ ] `pytest -q` passes locally.
* [ ] `black` / `isort` / `flake8` emit no warnings.
* [ ] CI pipeline is green.
* [ ] No unresolved Supervisor comments.
* [ ] PR title follows semantic commit style (e.g., **feat:** …, **fix:** …).

CI will additionally:

* Verify ≥ 90 % coverage (Phase 5 target).
* Run **mkdocs build --strict** once docs phase is enabled.

---

## 7. Supervisor Review Loop

1. After tests pass, push your branch.
2. The **Supervisor LLM** automatically reviews the PR:

   * If it replies `approved: true`, a maintainer merges.
   * If `approved: false`, address the `comments` list, then push again.
3. Repeat until approval.

---

## 8. Code of Conduct

Be respectful. Harassment or discrimination will not be tolerated.
We follow the [Contributor Covenant v2.1](https://www.contributor-covenant.org/).

---

## 9. License

By contributing, you agree your work is released under the repository’s
MIT License.

---

Happy hacking! 🚀

```
