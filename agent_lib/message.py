"""Message handling for AutoGen agent communication.

This module provides the Message class and utilities for parsing JSON-in-Markdown
format messages as specified in PROMPT-GUIDELINES.md.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Message:
    """Represents a message in the AutoGen conversation."""

    role: str
    content: str
    type: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Message to a dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "type": self.type,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of the Message in JSON-in-Markdown format."""
        return f"```json\n{json.dumps(self.to_dict(), indent=2)}\n```"

    def __repr__(self) -> str:
        """String representation of the Message for debugging."""
        return (
            f"Message(role={self.role!r}, type={self.type!r}, "
            f"content={self.content[:50]!r}...)"
        )


def parse_message_block(text: str) -> Message:
    """Parse a JSON-in-Markdown message block into a Message object.

    Args:
        text: The message text containing JSON in markdown fences

    Returns:
        Parsed Message object

    Raises:
        ValueError: If the message format is invalid
    """
    # Extract JSON from markdown fences
    json_match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON block found in message")

    json_text = json_match.group(1)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in message: {e}")

    return Message(
        role=data["role"],
        content=data["content"],
        type=data["type"],
        metadata=data.get("metadata", {}),
    )


def format_message_block(message: Message) -> str:
    """Format a Message object as JSON-in-Markdown.

    Args:
        message: The message to format

    Returns:
        Formatted message string
    """
    return str(message)


def send_message(message: Message) -> None:
    """Send a message in the AutoGen system.

    This is a placeholder that will be mocked in tests.

    Args:
        message: The message to send
    """
    # This will be implemented properly in the actual AutoGen integration
    pass
