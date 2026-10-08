import asyncio

from app.brain import decide
from app.capabilities import CapabilityResult
from app.models import Budget, CapabilityType, SourceClass


class FakeLLMCapability:
    capability_type = CapabilityType.LLM_REASONING

    def __init__(self, content):
        self.content = content
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        return CapabilityResult(
            capability=request.capability,
            success=True,
            data={"content": self.content},
        )


class FakeRegistry:
    def __init__(self, capability):
        self.capability = capability

    def get(self, capability_type):
        assert capability_type == CapabilityType.LLM_REASONING
        return self.capability


def test_decide_accepts_valid_brain_structured_query():
    llm = FakeLLMCapability(
        '{"decision_version":"1",'
        '"intent":"structured_document_query",'
        '"task_type":"CORPORATE_KNOWLEDGE",'
        '"source_policy":["CORPORATE"],'
        '"required_capabilities":["STRUCTURED_QUERY"],'
        '"plan":[{"step_id":"structured-query",'
        '"capability":"STRUCTURED_QUERY",'
        '"input":{"source_file":"DfQueryToExcel (7.1).xls",'
        '"sheet":"Export-D2",'
        '"filters":[{"column":"Край","operator":"gte","value":"05.10.2026"},'
        '{"column":"Край","operator":"lte","value":"31.01.2027"}]}}],'
        '"clarification_required":false,'
        '"reason":"exact structured document query"}'
    )

    decision, mode = asyncio.run(decide(
        "Покажи договорите от DfQueryToExcel (7.1).xls с крайна дата до 31.01.2027.",
        [SourceClass.CORPORATE],
        Budget(),
        FakeRegistry(llm),
    ))

    assert mode == "brain"
    assert decision.required_capabilities == [CapabilityType.STRUCTURED_QUERY]
    assert decision.plan[0].input["source_file"] == "DfQueryToExcel (7.1).xls"
    assert len(llm.calls) == 1
