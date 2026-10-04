from __future__ import annotations

from .budgets import BudgetController, BudgetExceeded
from .capabilities import CapabilityRequest, CapabilityResult
from .evidence import normalize_corporate_evidence, normalize_web_evidence
from .evidence_evaluation import EvidenceEvaluationResult, evaluate_evidence
from .conflict import ConflictAnalysisResult, analyze_conflicts
from .verification import verify_evidence_support
from .semantic_verification import (
    SemanticVerificationStatus,
    verify_answer_semantically,
    verify_claims_semantically,
)
from .synthesis import build_synthesis_messages, parse_synthesis_result
from .retrieval_refinement import (
    build_refinement_messages,
    parse_refinement_result,
)
from .web_research import (
    build_web_fetch_selection_messages,
    parse_web_fetch_selection,
)
from .models import (
    CapabilityType,
    EvidenceStatus,
    Plan,
    PlanStep,
    QuestionResolution,
    SemanticVerificationItem,
    StepStatus,
    SynthesisResult,
    Task,
    TaskState,
)
from .planner import build_plan
from .retrieval_strategy import merge_unique_candidates
from .registry import CapabilityRegistry


class Orchestrator:
    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self.registry = registry or CapabilityRegistry()

    async def refine_retrieval_query(
        self,
        task: Task,
        evidence,
        budget: BudgetController,
    ):
        messages = build_refinement_messages(task, evidence)

        budget.consume_capability_call()

        result = await self.registry.get(CapabilityType.LLM_REASONING).execute(
            CapabilityRequest(
                capability=CapabilityType.LLM_REASONING,
                input={
                    "messages": messages,
                    "temperature": 0.0,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"},
                },
            )
        )

        if not result.success:
            raise RuntimeError(
                result.error or "Retrieval refinement failed"
            )

        content = result.data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Retrieval refinement returned empty content"
            )

        return parse_refinement_result(content)

    async def select_web_fetch_candidates(
        self,
        task: Task,
        evidence,
        budget: BudgetController,
    ):
        messages = build_web_fetch_selection_messages(task, evidence)

        budget.consume_capability_call()

        result = await self.registry.get(CapabilityType.LLM_REASONING).execute(
            CapabilityRequest(
                capability=CapabilityType.LLM_REASONING,
                input={
                    "messages": messages,
                    "temperature": 0.0,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"},
                },
            )
        )

        if not result.success:
            raise RuntimeError(
                result.error or "Web fetch selection failed"
            )

        content = result.data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Web fetch selection returned empty content"
            )

        return parse_web_fetch_selection(
            content,
            evidence,
            max_selections=task.budget.max_web_fetches,
        )

    async def synthesize_answer(
        self,
        task: Task,
        evidence,
        budget: BudgetController,
    ) -> SynthesisResult:
        budget.consume_capability_call()
        capability = self.registry.get(CapabilityType.LLM_REASONING)

        result = await capability.execute(
            CapabilityRequest(
                capability=CapabilityType.LLM_REASONING,
                input={
                    "messages": build_synthesis_messages(task, evidence),
                    "temperature": 0.0,
                    "max_tokens": 10000,
                    "response_format": {"type": "json_object"},
                },
            )
        )

        if not result.success:
            raise RuntimeError(result.error or "LLM synthesis failed")

        try:
            return parse_synthesis_result(
                answer=result.data["content"],
                evidence=evidence,
            )
        except ValueError as exc:
            finish_reason = result.data.get("finish_reason")
            usage = result.data.get("usage")
            raise RuntimeError(
                f"Synthesis JSON validation failed "
                f"(finish_reason={finish_reason}, usage={usage}): {exc}"
            ) from exc

    def create_plan(self, task: Task) -> Plan:
        task.state = TaskState.UNDERSTANDING
        plan = build_plan(task)
        task.state = TaskState.PLANNING
        return plan

    @staticmethod
    def should_retry_retrieval(resolution: QuestionResolution) -> bool:
        return resolution == QuestionResolution.INSUFFICIENT

    async def _execute_step(
        self,
        step,
        budget: BudgetController,
    ) -> CapabilityResult | None:
        budget.consume_step()

        if step.capability is None:
            step.status = StepStatus.SKIPPED
            return None

        step.status = StepStatus.RUNNING

        try:
            if step.capability == CapabilityType.WEB_SEARCH:
                budget.consume_web_search()
            elif step.capability == CapabilityType.WEB_FETCH:
                budget.consume_web_fetch()

            budget.consume_capability_call()
            capability = self.registry.get(step.capability)

            result = await capability.execute(
                CapabilityRequest(
                    capability=step.capability,
                    input=step.input,
                )
            )

            if result.success:
                step.status = StepStatus.COMPLETED
            else:
                step.status = StepStatus.FAILED

            return result

        except Exception:
            step.status = StepStatus.FAILED
            raise

    async def execute_plan(
        self,
        task: Task,
        plan: Plan,
    ) -> tuple[
        list[CapabilityResult],
        EvidenceEvaluationResult,
        ConflictAnalysisResult,
        SynthesisResult,
        object,
    ]:
        task.state = TaskState.EXECUTING
        budget = BudgetController(task.budget)
        results: list[CapabilityResult] = []
        retrieved_candidates: list[dict] = []
        web_evidence_candidates: list[dict] = []

        async def execute_retrieval_step(step: PlanStep) -> CapabilityResult | None:
            try:
                budget.consume_retrieval_round()
            except BudgetExceeded:
                return None

            result = await self._execute_step(step, budget)

            if result is not None:
                results.append(result)
                if (
                    result.success
                    and result.capability == CapabilityType.CORPORATE_RETRIEVAL
                ):
                    retrieved_candidates[:] = merge_unique_candidates(
                        retrieved_candidates,
                        result.data.get("results", []),
                    )

            return result

        completed_step_ids: set[str] = set()

        for step in plan.steps:
            if any(dependency not in completed_step_ids for dependency in step.depends_on):
                step.status = StepStatus.SKIPPED
                continue

            if step.capability == CapabilityType.CORPORATE_RETRIEVAL:
                result = await execute_retrieval_step(step)
                if result is None:
                    step.status = StepStatus.SKIPPED
                    continue

                if result.success:
                    completed_step_ids.add(step.step_id)
            else:
                result = await self._execute_step(step, budget)
                if result is not None:
                    results.append(result)

                    if result.success:
                        completed_step_ids.add(step.step_id)

                    if (
                        result.success
                        and result.capability in (
                            CapabilityType.WEB_SEARCH,
                            CapabilityType.WEB_FETCH,
                        )
                    ):
                        evidence = result.data.get("evidence", [])
                        if isinstance(evidence, list):
                            web_evidence_candidates.extend(evidence)

        # Web research is deliberately two-phase:
        # search first, then selectively fetch only sources chosen from
        # the already retrieved evidence.
        if web_evidence_candidates:
            search_step_ids = {
                step.step_id
                for step in plan.steps
                if (
                    step.capability == CapabilityType.WEB_SEARCH
                    and step.status == StepStatus.COMPLETED
                )
            }

            if search_step_ids and budget.usage.web_fetches < task.budget.max_web_fetches:
                web_search_evidence = normalize_web_evidence(
                    web_evidence_candidates
                )

                try:
                    selection = await self.select_web_fetch_candidates(
                        task,
                        web_search_evidence,
                        budget,
                    )
                except BudgetExceeded:
                    selection = None

                if selection is not None:
                    evidence_by_id = {
                        item.evidence_id: item
                        for item in web_search_evidence
                    }

                    fetch_source_ids: set[str] = set()

                    for evidence_id in selection.evidence_ids:
                        item = evidence_by_id.get(evidence_id)
                        if item is None or not item.source_location:
                            continue

                        if item.source_location in fetch_source_ids:
                            continue

                        if budget.usage.web_fetches >= task.budget.max_web_fetches:
                            break

                        if len(plan.steps) >= plan.max_steps:
                            break

                        fetch_source_ids.add(item.source_location)

                        fetch_step = PlanStep(
                            step_id=f"web-fetch-{budget.usage.web_fetches + 1}",
                            type="FETCH_WEB_SELECTED",
                            capability=CapabilityType.WEB_FETCH,
                            input={"url": item.source_location},
                            depends_on=[next(iter(search_step_ids))],
                            evidence_required=True,
                        )

                        plan.steps.append(fetch_step)

                        result = await self._execute_step(
                            fetch_step,
                            budget,
                        )

                        if result is not None:
                            results.append(result)

                            if result.success:
                                completed_step_ids.add(fetch_step.step_id)

                                evidence = result.data.get("evidence", [])
                                if isinstance(evidence, list):
                                    web_evidence_candidates.extend(evidence)

        while True:
            plan.status = "EXECUTED"

            task.state = TaskState.EVIDENCE_EVALUATION

            all_evidence = normalize_corporate_evidence(
                retrieved_candidates
            )
            all_evidence.extend(
                normalize_web_evidence(web_evidence_candidates)
            )

            evaluation = evaluate_evidence(all_evidence)

            task.state = TaskState.CONFLICT_ANALYSIS
            conflicts = analyze_conflicts(evaluation.applicable)

            task.state = TaskState.EXECUTING
            synthesis = await self.synthesize_answer(
                task,
                evaluation.applicable,
                budget,
            )

            if synthesis.resolution != QuestionResolution.INSUFFICIENT:
                break

            task.state = TaskState.MORE_EVIDENCE_REQUIRED

            if budget.usage.retrieval_rounds >= task.budget.max_retrieval_rounds:
                break

            try:
                refinement = await self.refine_retrieval_query(
                    task,
                    all_evidence,
                    budget,
                )
            except BudgetExceeded:
                break

            refined_query = refinement.query
            if not refined_query:
                break

            current_query = (task.normalized_question or task.user_request).strip()
            if refined_query.strip() == current_query:
                break

            retry_step = PlanStep(
                step_id=f"corporate-retrieval-{budget.usage.retrieval_rounds + 1}",
                type="RETRIEVE_CORPORATE_EVIDENCE_REFINED",
                capability=CapabilityType.CORPORATE_RETRIEVAL,
                input={
                    **(
                        plan.steps[0].input
                        if plan.steps
                        and plan.steps[0].capability == CapabilityType.CORPORATE_RETRIEVAL
                        else {}
                    ),
                    "query": refined_query,
                },
                evidence_required=True,
            )

            if len(plan.steps) >= plan.max_steps:
                break

            plan.steps.append(retry_step)

            result = await execute_retrieval_step(retry_step)
            if result is None:
                break


        if synthesis.resolution == QuestionResolution.ANSWERABLE:
            evaluation.status = EvidenceStatus.SUPPORTED
        elif synthesis.resolution == QuestionResolution.CONFLICTED:
            evaluation.status = EvidenceStatus.CONFLICT
        else:
            evaluation.status = EvidenceStatus.INSUFFICIENT_EVIDENCE

        if synthesis.resolution == QuestionResolution.AMBIGUOUS:
            task.state = TaskState.CLARIFICATION_REQUIRED
        else:
            task.state = TaskState.VERIFICATION

        conflict_errors = [
            conflict.description
            for conflict in conflicts.conflicts
        ]

        verification = verify_evidence_support(
            claims=synthesis.material_claims,
            evidence=evaluation.applicable,
            citations=synthesis.evidence_ids,
            conflict_errors=conflict_errors,
        )

        semantic_results = []
        semantic_errors = []

        if (
            synthesis.resolution == QuestionResolution.ANSWERABLE
            and verification.passed
        ):
            try:
                semantic_results = await verify_claims_semantically(
                    task=task,
                    claims=synthesis.material_claims,
                    evidence=evaluation.applicable,
                    budget=budget,
                    registry=self.registry,
                )
            except (BudgetExceeded, RuntimeError, ValueError) as exc:
                semantic_errors.append(str(exc))

            verification.semantic_results = [
                SemanticVerificationItem(
                    claim_index=index,
                    status=result.status.value,
                    reason=result.reason,
                )
                for index, result in enumerate(semantic_results)
            ]
            verification.semantic_errors = semantic_errors

            semantic_failed = (
                bool(semantic_errors)
                or len(semantic_results) != len(synthesis.material_claims)
                or any(
                    result.status != SemanticVerificationStatus.SUPPORTED
                    for result in semantic_results
                )
            )

            if semantic_failed:
                verification.passed = False
                verification.reason = (
                    "Semantic evidence verification failed."
                )
            else:
                verification.reason = (
                    "Evidence traceability and semantic verification checks passed."
                )

                try:
                    answer_semantic_result = await verify_answer_semantically(
                        task=task,
                        answer=synthesis.answer,
                        claims=synthesis.material_claims,
                        evidence=evaluation.applicable,
                        budget=budget,
                        registry=self.registry,
                    )
                except (BudgetExceeded, RuntimeError, ValueError) as exc:
                    verification.semantic_errors.append(
                        f"Final answer semantic verification failed: {exc}"
                    )
                    verification.passed = False
                    verification.reason = (
                        "Final answer semantic verification failed."
                    )
                else:
                    if (
                        answer_semantic_result.status
                        != SemanticVerificationStatus.SUPPORTED
                    ):
                        verification.semantic_errors.append(
                            "Final answer semantic verification: "
                            f"{answer_semantic_result.status.value}: "
                            f"{answer_semantic_result.reason}"
                        )
                        verification.passed = False
                        verification.reason = (
                            "Final answer semantic verification failed."
                        )

        if synthesis.resolution == QuestionResolution.AMBIGUOUS:
            task.state = TaskState.CLARIFICATION_REQUIRED
        elif synthesis.resolution in (
            QuestionResolution.INSUFFICIENT,
            QuestionResolution.CONFLICTED,
        ):
            task.state = TaskState.NO_ANSWER
        elif verification.passed:
            task.state = TaskState.ANSWER
        else:
            task.state = TaskState.NO_ANSWER

        return (
            results,
            evaluation,
            conflicts,
            synthesis,
            verification,
        )
