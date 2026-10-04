from __future__ import annotations

from pydantic import Field

from .models import ConversationContext, ConversationMessage


def build_conversation_context(messages: list[dict]) -> ConversationContext:
    normalized: list[ConversationMessage] = []

    for message in messages[-12:]:
        role = str(message.get("role", "unknown")).strip()
        content = message.get("content")

        if not isinstance(content, str):
            continue

        content = content.strip()
        if not content:
            continue

        normalized.append(
            ConversationMessage(
                role=role,
                content=content,
            )
        )

    latest_user = next(
        (message.content for message in reversed(normalized) if message.role == "user"),
        None,
    )
    latest_assistant = next(
        (message.content for message in reversed(normalized) if message.role == "assistant"),
        None,
    )

    return ConversationContext(
        messages=normalized,
        latest_user_message=latest_user,
        latest_assistant_message=latest_assistant,
    )
