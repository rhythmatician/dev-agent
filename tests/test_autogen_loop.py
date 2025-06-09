from agent_lib.message import Message
from agent_loop import run_autogen_loop


def test_autogen_loop_emits_valid_patch(monkeypatch, tmp_path: str) -> None:
    """DevAgent emits a patch or NO_PATCH_NEEDED in response to Supervisor's spec."""

    # 1. Provide mock config
    config_path = tmp_path / "agent.config.yaml"
    config_path.write_text(
        """
agents:
  supervisor:
    backend: mock
    model: gpt-o3
  dev_agent:
    backend: mock
    model: codellama-13b
"""
    )

    # 2. Patch LLMClient to emit a fixed message
    class FakeLLMClient:
        def __init__(self, backend, model) -> None:
            pass

        def complete(self, prompt):  # Returns a DevAgent-style diff message
            return """```json
{
  "role": "DevAgent",
  "type": "patch",
  "content": "```diff\\n--- a/file.py\\n+++ b/file.py\\n@@\\n+ fix\\n```",
  "metadata": {
    "iteration": 1,
    "test_name": "tests/test_foo.py::test_bar",
    "approved": null
  }
}
```"""

    monkeypatch.setattr("agent_lib.llm_client.LLMClient", FakeLLMClient)

    # 3. Capture emitted messages
    emitted = []

    def fake_send(message: Message):
        emitted.append(message)

    monkeypatch.setattr("agent_loop.send_message", fake_send)

    # 4. Run
    run_autogen_loop(config_path=str(config_path))

    # 5. Assert: At least one DevAgent patch or NO_PATCH_NEEDED emitted
    roles = [m.role for m in emitted]
    types = [m.type for m in emitted]

    assert "DevAgent" in roles
    assert any(t in ("patch", "status") for t in types)
    assert any(t in ("patch", "status") for t in types)


def test_supervisor_approval_triggers_git_tool(monkeypatch, tmp_path) -> None:
    """When Supervisor approves, GitTool should be invoked."""

    # 1. Setup mock config
    config_path = tmp_path / "agent.config.yaml"
    config_path.write_text(
        """
agents:
  supervisor:
    backend: mock
    model: gpt-o3
  dev_agent:
    backend: mock
    model: codellama-13b
max_iterations: 1
"""
    )

    # 2. Mock LLMClient (not used directly in this test)
    class FakeLLMClient:
        def __init__(self, backend, model) -> None:
            pass

        def complete(self, prompt) -> str:
            return "Mock response"

    monkeypatch.setattr("agent_lib.llm_client.LLMClient", FakeLLMClient)

    # 3. Capture emitted messages
    emitted = []

    def fake_send(message: Message):
        emitted.append(message)

    monkeypatch.setattr("agent_loop.send_message", fake_send)

    # 4. Run
    run_autogen_loop(config_path=str(config_path))

    # 5. Assert: GitTool should be invoked when Supervisor approves
    roles = [m.role for m in emitted]

    assert "DevAgent" in roles, "DevAgent should emit a patch"
    assert "Supervisor" in roles, "Supervisor should review the patch"
    assert "GitTool" in roles, "GitTool should be invoked after approval"

    # Check the sequence
    dev_agent_msgs = [m for m in emitted if m.role == "DevAgent"]
    supervisor_msgs = [m for m in emitted if m.role == "Supervisor"]
    git_tool_msgs = [m for m in emitted if m.role == "GitTool"]

    assert len(dev_agent_msgs) >= 1, "Should have at least one DevAgent message"
    assert len(supervisor_msgs) >= 1, "Should have at least one Supervisor message"
    assert len(git_tool_msgs) >= 1, "Should have at least one GitTool message"

    # Verify approval
    assert supervisor_msgs[0].metadata.get("approved") is True


def test_supervisor_rejection_blocks_git_tool(monkeypatch, tmp_path) -> None:
    """When Supervisor rejects, GitTool should NOT be invoked."""

    # 1. Setup mock config
    config_path = tmp_path / "agent.config.yaml"
    config_path.write_text(
        """
agents:
  supervisor:
    backend: mock
    model: gpt-o3
  dev_agent:
    backend: mock
    model: codellama-13b
max_iterations: 1
"""
    )

    # 2. Mock LLMClient
    class FakeLLMClient:
        def __init__(self, backend, model) -> None:
            pass

        def complete(self, prompt) -> str:
            return "Mock response"

    monkeypatch.setattr("agent_lib.llm_client.LLMClient", FakeLLMClient)

    # 3. Mock supervisor to reject the patch
    def mock_supervisor_review(patch_message: Message) -> Message:
        return Message(
            role="Supervisor",
            type="review",
            content="Patch is too broad - please make a more targeted fix.",
            metadata={
                "approved": False,
                "iteration": patch_message.metadata["iteration"],
            },
        )

    monkeypatch.setattr("agent_loop._supervisor_review", mock_supervisor_review)

    # 4. Capture emitted messages
    emitted = []

    def fake_send(message: Message):
        emitted.append(message)

    monkeypatch.setattr("agent_loop.send_message", fake_send)

    # 5. Run
    run_autogen_loop(config_path=str(config_path))

    # 6. Assert: GitTool should NOT be invoked when Supervisor rejects
    roles = [m.role for m in emitted]

    assert "DevAgent" in roles, "DevAgent should emit a patch"
    assert "Supervisor" in roles, "Supervisor should review the patch"
    assert "GitTool" not in roles, "GitTool should NOT be invoked after rejection"

    # Verify rejection
    supervisor_msgs = [m for m in emitted if m.role == "Supervisor"]
    assert len(supervisor_msgs) >= 1, "Should have at least one Supervisor message"
    assert supervisor_msgs[0].metadata.get("approved") is False


def test_message_format_follows_prompt_guidelines(monkeypatch, tmp_path) -> None:
    """All messages should follow JSON-in-Markdown format per PROMPT-GUIDELINES.md."""

    # 1. Setup mock config
    config_path = tmp_path / "agent.config.yaml"
    config_path.write_text(
        """
agents:
  supervisor:
    backend: mock
    model: gpt-o3
  dev_agent:
    backend: mock
    model: codellama-13b
max_iterations: 1
"""
    )

    # 2. Mock LLMClient
    class FakeLLMClient:
        def __init__(self, backend, model) -> None:
            pass

        def complete(self, prompt) -> str:
            return "Mock response"

    monkeypatch.setattr("agent_lib.llm_client.LLMClient", FakeLLMClient)

    # 3. Capture emitted messages
    emitted = []

    def fake_send(message: Message):
        emitted.append(message)

    monkeypatch.setattr("agent_loop.send_message", fake_send)

    # 4. Run
    run_autogen_loop(config_path=str(config_path))

    # 5. Assert: All messages follow the expected format
    assert len(emitted) > 0, "Should emit at least one message"

    for msg in emitted:
        # Required fields per PROMPT-GUIDELINES.md
        assert hasattr(msg, "role"), "Message should have 'role' field"
        assert hasattr(msg, "content"), "Message should have 'content' field"
        assert hasattr(msg, "type"), "Message should have 'type' field"
        assert hasattr(msg, "metadata"), "Message should have 'metadata' field"

        # Role should be one of the expected values
        assert msg.role in [
            "DevAgent",
            "Supervisor",
            "ShellTool",
            "GitTool",
        ], f"Unexpected role: {msg.role}"

        # Type should be one of the expected values
        assert msg.type in [
            "instruction",
            "patch",
            "output",
            "status",
            "review",
        ], f"Unexpected type: {msg.type}"

        # Metadata should be a dict
        assert isinstance(msg.metadata, dict), "Metadata should be a dictionary"
