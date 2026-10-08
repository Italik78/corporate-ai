from app.brain import BrainDecision, BrainPlanStep
from app.models import CapabilityType, SourceClass, Task, TaskType
from app.planner import build_plan


def test_brain_structured_query_becomes_runtime_step():
    task = Task(
        user_request="Покажи договорите от таблицата.",
        normalized_question="Покажи договорите от таблицата.",
        task_type=TaskType.CORPORATE_KNOWLEDGE,
        allowed_source_classes=[SourceClass.CORPORATE],
    )

    decision = BrainDecision(
        decision_version="1",
        intent="structured_document_query",
        task_type=TaskType.CORPORATE_KNOWLEDGE,
        source_policy=[SourceClass.CORPORATE],
        required_capabilities=[CapabilityType.STRUCTURED_QUERY],
        plan=[
            BrainPlanStep(
                step_id="structured-query",
                capability=CapabilityType.STRUCTURED_QUERY,
                input={
                    "source_file": "DfQueryToExcel (7.1).xls",
                    "sheet": "Export-D2",
                    "filters": [
                        {
                            "column": "Край",
                            "operator": "gte",
                            "value": "05.10.2026",
                        }
                    ],
                },
            )
        ],
        reason="exact structured document query",
    )

    plan = build_plan(task, decision)

    assert len(plan.steps) == 1
    assert plan.steps[0].step_id == "structured-query"
    assert plan.steps[0].type == "STRUCTURED_DOCUMENT_QUERY"
    assert plan.steps[0].capability == CapabilityType.STRUCTURED_QUERY
    assert plan.steps[0].evidence_required is True


def test_brain_structured_query_preserves_exact_input():
    task = Task(
        user_request="Покажи договорите от таблицата.",
        normalized_question="Покажи договорите от таблицата.",
        task_type=TaskType.CORPORATE_KNOWLEDGE,
        allowed_source_classes=[SourceClass.CORPORATE],
    )

    exact_input = {
        "source_file": "DfQueryToExcel (7.1).xls",
        "sheet": "Export-D2",
        "filters": [
            {
                "column": "Край",
                "operator": "lte",
                "value": "31.01.2027",
            }
        ],
        "columns": ["Номер", "Описание", "Край"],
        "limit": 9,
    }

    decision = BrainDecision(
        decision_version="1",
        intent="structured_document_query",
        task_type=TaskType.CORPORATE_KNOWLEDGE,
        source_policy=[SourceClass.CORPORATE],
        required_capabilities=[CapabilityType.STRUCTURED_QUERY],
        plan=[
            BrainPlanStep(
                step_id="structured-query",
                capability=CapabilityType.STRUCTURED_QUERY,
                input=exact_input,
            )
        ],
        reason="exact structured document query",
    )

    plan = build_plan(task, decision)

    assert plan.steps[0].input == exact_input
