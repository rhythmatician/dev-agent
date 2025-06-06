# 🛠️ Dev Agent — Project Outline

This outline defines each feature-driven, test-driven development (TDD) phase for the **Dev Agent** repository.
Every phase follows the RED → GREEN → REFACTOR loop:

1. **RED** — add one or more failing tests.
2. **GREEN** — implement the minimal code to pass.
3. **REFACTOR** — clean up, document, and merge.

---

## Phase Roadmap

| Phase | Goal                                   | “Definition of Done”                                                        |
|-------|----------------------------------------|-----------------------------------------------------------------------------|
| **0** | **Repository & CI Scaffold**           | • Repo initialized<br>• `black`, `isort`, `pytest` pre-commit hooks<br>• CI workflow running tests & style checks |
| **1** | **Test-Runner Module**                 | • `agent_lib/test_runner.py` runs the project’s test command<br>• Returns structured results (passed / failures list)<br>• Unit tests cover pass & fail paths |
| **2** | **LLM Patch-Generator Module**         | • `agent_lib/llm_patch_generator.py` prompts a local model and returns a valid unified diff<br>• Validates diff via `git apply --check` |
| **3** | **Orchestrator Loop**                  | • `dev_agent.py` ties together runner, patcher, and git tools<br>• Iterates until tests pass or `max_iterations` hit<br>• Commits to a branch `dev-agent/fix-*` |
| **4** | **CI / Packaging / Config**            | • Installable via `pip` (`pyproject.toml`)<br>• `agent.config.yaml` loaded & validated<br>• Reusable GitHub Action published |
| **5** | **Advanced Features & Maintenance**    | • Multiple LLM backends (llama-cpp, Ollama)<br>• Optional auto-PR creation<br>• Metrics/report generation<br>• ≥90 % test coverage |

---

## Working Practices

- **Every new capability starts with a failing test.**
- Branch naming: `feat/<slug>` or `fix/<slug>`; auto-generated patches use `dev-agent/fix-<test>`.
- Commits created by the agent use the prefix `TDD:` followed by a brief description.
- Pull requests must show **green CI** *and* zero pending review comments before merge.

---

_This document is intentionally lean; Copilot (or any dev agent) should expand upon each phase with more granular tasks as it implements them._
