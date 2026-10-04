from __future__ import annotations

from .context import build_conversation_context
from .models import SourceClass, Task, TaskType


_CORPORATE_TERMS = (
    "служител",
    "служители",
    "договор",
    "договорът",
    "политика",
    "политиката",
    "процедура",
    "процедурата",
    "вътрешен",
    "вътрешна",
    "компания",
    "дружество",
    "отдел",
    "отпуск",
    "заплата",
    "възнаграждение",
    "поддръжка",
    "техническа поддръжка",
    "sla",
    "клиентски договор",
)

_WEB_TERMS = (
    "интернет",
    "онлайн",
    "уеб",
    "web",
    "актуално",
    "последни",
    "последна информация",
    "днес",
    "новини",
    "публична",
    "публични",
    "официален",
    "официална",
    "официалния",
    "актуалните цени",
    "current",
    "latest",
    "today",
    "official website",
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(term in normalized for term in terms)


def classify_task(
    user_request: str,
    source_policy: list[SourceClass],
) -> TaskType:
    text = user_request.strip()

    if not text:
        return TaskType.UNKNOWN

    corporate_allowed = SourceClass.CORPORATE in source_policy
    web_allowed = SourceClass.WEB in source_policy

    corporate_signal = _contains_any(text, _CORPORATE_TERMS)
    web_signal = _contains_any(text, _WEB_TERMS)

    if corporate_signal and web_allowed and web_signal:
        return TaskType.CORPORATE_AND_WEB

    if corporate_signal and corporate_allowed:
        return TaskType.CORPORATE_KNOWLEDGE

    if web_signal and web_allowed:
        return TaskType.WEB_RESEARCH

    if corporate_allowed and not web_allowed:
        return TaskType.CORPORATE_KNOWLEDGE

    if web_allowed and not corporate_allowed:
        return TaskType.WEB_RESEARCH

    return TaskType.GENERAL


def detect_missing_context(user_request: str, task_type: TaskType) -> list[str]:
    text = user_request.strip().casefold()
    missing: list[str] = []

    if task_type == TaskType.CORPORATE_KNOWLEDGE:
        if any(term in text for term in ("по договора", "по договор", "договорът")):
            if not any(term in text for term in ("номер", "№", "име", "наименование", "клиент", "доставчик")):
                missing.append("идентификация на договора")

    return missing


def resolve_contextual_question(user_request: str, known_context: list[str]) -> str:
    question = " ".join(user_request.split())
    if not known_context:
        return question

    normalized = question.casefold()
    contextual_terms = ("него", "нея", "това", "този", "тази", "тези", "там", "тогава")
    if not any(term in normalized for term in contextual_terms):
        return question

    return question


def build_task(
    user_request: str,
    *,
    conversation_id: str | None = None,
    source_policy: list[SourceClass] | None = None,
    requested_freshness: str | None = None,
    answer_constraints=None,
    budget=None,
    messages: list[dict] | None = None,
) -> Task:
    policy = source_policy if source_policy is not None else [SourceClass.CORPORATE]

    task_type = classify_task(user_request, policy)
    conversation_context = build_conversation_context(messages or [])
    known_context = [f"{message.role}: {message.content}" for message in conversation_context.messages]
    normalized_question = resolve_contextual_question(user_request, known_context)

    return Task(
        conversation_id=conversation_id,
        user_request=user_request,
        normalized_question=normalized_question,
        task_type=task_type,
        known_context=known_context,
        conversation_context=conversation_context,
        allowed_source_classes=policy,
        requested_freshness=requested_freshness,
        **({"answer_constraints": answer_constraints} if answer_constraints is not None else {}),
        **({"budget": budget} if budget is not None else {}),
    )
