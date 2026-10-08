from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .capabilities import CapabilityRequest
from .models import Budget, CapabilityType, SourceClass, TaskType
from .registry import CapabilityRegistry
from .task import classify_task


class BrainPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str = Field(min_length=1, max_length=64)
    capability: CapabilityType
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class BrainDecision(BaseModel):
    """Versioned operational routing decision; intentionally has no CoT field."""

    model_config = ConfigDict(extra="forbid")
    decision_version: str = Field(pattern=r"^1$")
    intent: str = Field(min_length=1, max_length=80)
    task_type: TaskType
    source_policy: list[SourceClass]
    required_capabilities: list[CapabilityType]
    plan: list[BrainPlanStep] = Field(max_length=12)
    clarification_required: bool = False
    reason: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_plan(self):
        ids = [step.step_id for step in self.plan]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate plan step id")
        known: set[str] = set()
        for step in self.plan:
            if any(dependency not in known for dependency in step.depends_on):
                raise ValueError("plan dependencies must reference earlier steps")
            known.add(step.step_id)
        if not set(self.required_capabilities).issubset({s.capability for s in self.plan}):
            raise ValueError("required capability missing from plan")
        return self


class BrainDecisionRejected(ValueError):
    pass


def validate_decision(
    raw: str | dict[str, Any],
    *,
    question: str,
    allowed_sources: list[SourceClass],
    budget: Budget,
) -> BrainDecision:
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        decision = BrainDecision.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise BrainDecisionRejected(str(exc)) from exc
    if len(decision.plan) > budget.max_steps:
        raise BrainDecisionRejected("plan exceeds max_steps")
    if not set(decision.source_policy).issubset(set(allowed_sources)):
        raise BrainDecisionRejected("decision attempts to elevate source policy")
    if len(decision.source_policy) != len(set(decision.source_policy)):
        raise BrainDecisionRejected("duplicate source policy")
    permitted = {
        CapabilityType.CORPORATE_RETRIEVAL,
        CapabilityType.STRUCTURED_QUERY,
        CapabilityType.WEB_SEARCH,
        CapabilityType.WEB_FETCH,
        CapabilityType.GENERAL_RESPONSE,
    }
    if not set(decision.required_capabilities).issubset(permitted):
        raise BrainDecisionRejected("capability is not allowed by control plane")
    for step in decision.plan:
        if step.capability not in permitted:
            raise BrainDecisionRejected("capability is not allowed by control plane")
        if step.capability == CapabilityType.GENERAL_RESPONSE and decision.task_type != TaskType.GENERAL:
            raise BrainDecisionRejected("general response capability is only allowed for GENERAL tasks")
        if step.capability in (CapabilityType.CORPORATE_RETRIEVAL, CapabilityType.STRUCTURED_QUERY) and SourceClass.CORPORATE not in allowed_sources:
            raise BrainDecisionRejected("corporate capability is not authorized")
        if step.capability in (CapabilityType.WEB_SEARCH, CapabilityType.WEB_FETCH) and SourceClass.WEB not in allowed_sources:
            raise BrainDecisionRejected("web capability is not authorized")
        if step.capability in (CapabilityType.CORPORATE_RETRIEVAL, CapabilityType.STRUCTURED_QUERY) and SourceClass.CORPORATE not in decision.source_policy:
            raise BrainDecisionRejected("plan uses a source omitted from its policy")
        if step.capability == CapabilityType.STRUCTURED_QUERY:
            has_source_file = bool(str(step.input.get("source_file", "")).strip())
            has_document_ref = bool(
                str(step.input.get("document_id", "")).strip()
            ) and step.input.get("version") is not None

            if has_source_file and has_document_ref:
                raise BrainDecisionRejected(
                    "structured query cannot combine source_file with document_id/version"
                )
            if not has_source_file and not has_document_ref:
                raise BrainDecisionRejected(
                    "structured query requires exact source_file or document_id/version"
                )
        if step.capability in (CapabilityType.WEB_SEARCH, CapabilityType.WEB_FETCH) and SourceClass.WEB not in decision.source_policy:
            raise BrainDecisionRejected("plan uses a source omitted from its policy")
    if decision.task_type in (TaskType.CORPORATE_KNOWLEDGE, TaskType.CORPORATE_AND_WEB) and SourceClass.CORPORATE not in allowed_sources:
        raise BrainDecisionRejected("task type requires unauthorized corporate source")
    if decision.task_type in (TaskType.WEB_RESEARCH, TaskType.CORPORATE_AND_WEB) and SourceClass.WEB not in allowed_sources:
        raise BrainDecisionRejected("task type requires unauthorized web source")
    deterministic_type = classify_task(question, allowed_sources)
    required_for_type = {
        TaskType.CORPORATE_KNOWLEDGE: {SourceClass.CORPORATE},
        TaskType.WEB_RESEARCH: {SourceClass.WEB},
        TaskType.CORPORATE_AND_WEB: {SourceClass.CORPORATE, SourceClass.WEB},
    }
    if decision.task_type != deterministic_type:
        raise BrainDecisionRejected(
            "decision task type differs from deterministic source-policy classifier"
        )
    if not required_for_type.get(deterministic_type, set()).issubset(
        required_for_type.get(decision.task_type, set())
    ):
        raise BrainDecisionRejected("decision drops a deterministically required source class")
    if not required_for_type.get(decision.task_type, set()).issubset(set(decision.source_policy)):
        raise BrainDecisionRejected("decision task type exceeds its selected source policy")
    actual_capabilities = [step.capability for step in decision.plan]
    allowed_capability_plans = {
        TaskType.CORPORATE_KNOWLEDGE: {
            (CapabilityType.CORPORATE_RETRIEVAL,),
            (CapabilityType.STRUCTURED_QUERY,),
        },
        TaskType.WEB_RESEARCH: {
            (CapabilityType.WEB_SEARCH,),
        },
        TaskType.CORPORATE_AND_WEB: {
            (CapabilityType.CORPORATE_RETRIEVAL, CapabilityType.WEB_SEARCH),
        },
        TaskType.GENERAL: {
            (CapabilityType.GENERAL_RESPONSE,),
        },
    }
    actual_plan = tuple(actual_capabilities)
    if actual_plan not in allowed_capability_plans.get(decision.task_type, set()):
        raise BrainDecisionRejected("proposed plan is not allowed for the deterministic task type")
    if decision.required_capabilities != actual_capabilities:
        raise BrainDecisionRejected("required capabilities must match the proposed plan")
    if decision.task_type == TaskType.CORPORATE_AND_WEB and decision.plan[1].depends_on != [decision.plan[0].step_id]:
        raise BrainDecisionRejected("web fallback must depend on corporate retrieval")
    return decision


def deterministic_decision(question: str, allowed_sources: list[SourceClass], budget: Budget) -> BrainDecision:
    task_type = classify_task(question, allowed_sources)
    plan: list[BrainPlanStep] = []
    if task_type in (TaskType.CORPORATE_KNOWLEDGE, TaskType.CORPORATE_AND_WEB):
        plan.append(BrainPlanStep(step_id="corporate-retrieval-1", capability=CapabilityType.CORPORATE_RETRIEVAL))
    if task_type in (TaskType.WEB_RESEARCH, TaskType.CORPORATE_AND_WEB):
        deps = [plan[-1].step_id] if task_type == TaskType.CORPORATE_AND_WEB and plan else []
        plan.append(BrainPlanStep(step_id="web-search-1", capability=CapabilityType.WEB_SEARCH, depends_on=deps))
    if task_type == TaskType.GENERAL:
        plan.append(BrainPlanStep(step_id="general-response-1", capability=CapabilityType.GENERAL_RESPONSE))
    return BrainDecision(
        decision_version="1", intent="deterministic_fallback", task_type=task_type,
        source_policy=allowed_sources, required_capabilities=[step.capability for step in plan],
        plan=plan, reason="brain_unavailable_or_rejected",
    )


async def decide(
    question: str,
    allowed_sources: list[SourceClass],
    budget: Budget,
    registry: CapabilityRegistry,
) -> tuple[BrainDecision, str]:
    """Ask Qwen for a routing proposal, then validate; deterministic fallback is safe."""
    fallback = deterministic_decision(question, allowed_sources, budget)
    prompt = {
        "schema": BrainDecision.model_json_schema(),
        "decision_version": "1",
        "deterministic_task_type": classify_task(question, allowed_sources).value,
        "allowed_task_types": [item.value for item in TaskType],
        "allowed_source_policy": [item.value for item in allowed_sources],
        "allowed_capabilities": [item.value for item in (
        CapabilityType.CORPORATE_RETRIEVAL,
        CapabilityType.STRUCTURED_QUERY,
        CapabilityType.WEB_SEARCH,
        CapabilityType.WEB_FETCH,
        CapabilityType.GENERAL_RESPONSE,
    )],
        "max_steps": budget.max_steps,
    }
    try:
        result = await registry.get(CapabilityType.LLM_REASONING).execute(CapabilityRequest(
            capability=CapabilityType.LLM_REASONING,
            input={"messages": [
                {"role": "system", "content": (
                    "Return only one JSON object conforming exactly to the supplied version 1 schema. "
                    "This is an operational routing proposal, not tool execution. Never add fields or private reasoning. "
                    "Keep reason under 160 characters. You MUST use deterministic_task_type exactly; never add "
                    "a source class or omit a required source. For CORPORATE_AND_WEB, "
                    "include corporate retrieval followed by web search depending on it. The proposed plan covers "
                    "initial steps only: do not add WEB_FETCH, which the Control Plane schedules after selecting "
                    "returned search evidence. required_capabilities must list only the initial plan capabilities. "
                    "For CORPORATE_KNOWLEDGE, choose either CORPORATE_RETRIEVAL or STRUCTURED_QUERY. "
    "STRUCTURED_QUERY is for exact structured-document/table queries and must include exact input "
    "such as source_file or document_id+version; never invent result rows."
                )},
                {"role": "user", "content": json.dumps({"question": question, "contract": prompt}, ensure_ascii=False)},
            ], "temperature": 0.0, "max_tokens": 500, "response_format": {"type": "json_object"}},
        ))
        if not result.success:
            return fallback, "brain_unavailable"
        decision = validate_decision(result.data.get("content", ""), question=question, allowed_sources=allowed_sources, budget=budget)
        return decision, "brain"
    except Exception:
        return fallback, "deterministic_fallback"
