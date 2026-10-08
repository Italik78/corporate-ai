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
    AnswerStatus,
    CapabilityType,
    EvidenceStatus,
    SourceClass,
    Plan,
    PlanStep,
    QuestionResolution,
    SemanticVerificationItem,
    StepStatus,
    SynthesisResult,
    VerificationResult,
    EvidenceStatus,
    TaskType,
    Task,
    TaskState,
)
from .brain import BrainDecision
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

    def create_plan(
        self,
        task: Task,
        brain_decision: BrainDecision | None = None,
    ) -> Plan:
        task.state = TaskState.UNDERSTANDING
        plan = build_plan(task, brain_decision)
        task.state = TaskState.PLANNING
        return plan

    @staticmethod
    def should_retry_retrieval(resolution: QuestionResolution) -> bool:
        return resolution == QuestionResolution.INSUFFICIENT

    async def _execute_step(
        self,
        task: Task,
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

            capability_input = step.input
            if step.capability == CapabilityType.GENERAL_RESPONSE:
                history = [
                    message.model_dump()
                    for message in task.conversation_context.messages
                    if message.role in {"system", "user", "assistant"}
                ]
                if not any(message.get("role") == "user" for message in history):
                    history.append({"role": "user", "content": task.user_request})
                capability_input = {
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Answer general, non-corporate questions helpfully. "
                                "You have no tools and no corporate evidence. Do not "
                                "claim to have checked company records or current web sources. "
                                "If the user asks for current or company-specific facts, say "
                                "that this answer is ungrounded and request the appropriate research."
                            ),
                        },
                        *history[-12:],
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1500,
                }

            result = await capability.execute(
                CapabilityRequest(
                    capability=step.capability,
                    input=capability_input,
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
        structured_query_mode = any(
            step.capability == CapabilityType.STRUCTURED_QUERY
            for step in plan.steps
        )

        async def execute_retrieval_step(step: PlanStep) -> CapabilityResult | None:
            try:
                budget.consume_retrieval_round()
            except BudgetExceeded:
                return None

            result = await self._execute_step(task, step, budget)

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
                result = await self._execute_step(task, step, budget)
                if result is not None:
                    results.append(result)

                    if (
                        result.capability == CapabilityType.STRUCTURED_QUERY
                        and not result.success
                        and result.data.get("clarification_required") is True
                    ):
                        matches = result.data.get("matches", [])
                        source_file = result.data.get("source_file")

                        filenames = [
                            str(item.get("source_file", "")).strip()
                            for item in matches
                            if isinstance(item, dict)
                            and str(item.get("source_file", "")).strip()
                        ]
                        filenames = list(dict.fromkeys(filenames))

                        task.missing_context = (
                            [f"уточнение на файла: {name}" for name in filenames]
                            if filenames
                            else ["уточнение на файла"]
                        )
                        task.state = TaskState.CLARIFICATION_REQUIRED
                        plan.status = "EXECUTED"

                        if filenames:
                            clarification_question = (
                                f"Кой файл имате предвид за „{source_file}“? "
                                + " или ".join(
                                    f"„{name}“" for name in filenames
                                )
                                + "?"
                            )
                        else:
                            clarification_question = (
                                f"Моля, уточнете кой файл имате предвид за "
                                f"„{source_file}“."
                            )

                        evaluation = EvidenceEvaluationResult(
                            status=EvidenceStatus.INSUFFICIENT_EVIDENCE
                        )
                        conflicts = ConflictAnalysisResult()
                        synthesis = SynthesisResult(
                            answer="",
                            resolution=QuestionResolution.AMBIGUOUS,
                            needs_clarification=True,
                            clarification_question=clarification_question,
                            uncertainty="The requested corporate file reference is ambiguous.",
                        )
                        verification = VerificationResult(
                            passed=False,
                            reason="CLARIFICATION_REQUIRED_BEFORE_EVIDENCE_EXECUTION",
                        )

                        return (
                            results,
                            evaluation,
                            conflicts,
                            synthesis,
                            verification,
                        )

                    if result.success:
                        completed_step_ids.add(step.step_id)

                    if (
                        result.success
                        and result.capability == CapabilityType.STRUCTURED_QUERY
                    ):
                        rows = result.data.get("rows", [])
                        if isinstance(rows, list):
                            retrieved_candidates[:] = merge_unique_candidates(
                                retrieved_candidates,
                                rows,
                            )

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

        if task.task_type == TaskType.GENERAL:
            general_result = next(
                (item for item in results if item.success and item.data.get("content")),
                None,
            )
            answer = str(general_result.data["content"]) if general_result else ""
            synthesis = SynthesisResult(
                answer=answer,
                resolution=(
                    QuestionResolution.ANSWERABLE
                    if answer.strip()
                    else QuestionResolution.INSUFFICIENT
                ),
            )
            evaluation = EvidenceEvaluationResult(status=EvidenceStatus.NOT_REQUIRED)
            conflicts = ConflictAnalysisResult()
            verification = VerificationResult(
                passed=False,
                reason="GENERAL_RESPONSE_IS_NOT_CORPORATE_EVIDENCE_VERIFIED",
            )
            task.state = TaskState.ANSWER if answer.strip() else TaskState.NO_ANSWER
            plan.status = "EXECUTED"
            return results, evaluation, conflicts, synthesis, verification

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
                except (BudgetExceeded, RuntimeError, ValueError):
                    # Search snippets remain evidence candidates, but a broken
                    # selector must not crash the whole request or authorize
                    # an arbitrary fetch. Evaluation can still fail closed.
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
                            task,
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

            if structured_query_mode:
                break

            task.state = TaskState.MORE_EVIDENCE_REQUIRED

            web_search_already_ran = any(
                item.success and item.capability == CapabilityType.WEB_SEARCH
                for item in results
            )
            if (
                not web_search_already_ran
                and SourceClass.WEB in task.allowed_source_classes
                and budget.usage.web_searches < task.budget.max_web_searches
                and len(plan.steps) < plan.max_steps
            ):
                # Server policy may permit web fallback, but it is only used
                # after corporate evidence is evaluated as insufficient.
                search_step = PlanStep(
                    step_id=f"web-fallback-{budget.usage.web_searches + 1}",
                    type="SEARCH_WEB_FALLBACK",
                    capability=CapabilityType.WEB_SEARCH,
                    input={"query": task.normalized_question or task.user_request},
                    evidence_required=True,
                )
                plan.steps.append(search_step)
                search_result = await self._execute_step(task, search_step, budget)
                if search_result is not None:
                    results.append(search_result)
                    if search_result.success:
                        found = search_result.data.get("evidence", [])
                        if isinstance(found, list):
                            web_evidence_candidates.extend(found)

                if search_result is not None and search_result.success and web_evidence_candidates:
                    search_evidence = normalize_web_evidence(web_evidence_candidates)
                    try:
                        selection = await self.select_web_fetch_candidates(
                            task, search_evidence, budget
                        )
                    except (BudgetExceeded, RuntimeError, ValueError):
                        selection = None
                    evidence_by_id = {item.evidence_id: item for item in search_evidence}
                    for evidence_id in selection.evidence_ids if selection else []:
                        source = evidence_by_id.get(evidence_id)
                        if (
                            source is None
                            or not source.source_location
                            or budget.usage.web_fetches >= task.budget.max_web_fetches
                            or len(plan.steps) >= plan.max_steps
                        ):
                            continue
                        fetch_step = PlanStep(
                            step_id=f"web-fallback-fetch-{budget.usage.web_fetches + 1}",
                            type="FETCH_WEB_FALLBACK_SOURCE",
                            capability=CapabilityType.WEB_FETCH,
                            input={"url": source.source_location},
                            depends_on=[search_step.step_id],
                            evidence_required=True,
                        )
                        plan.steps.append(fetch_step)
                        fetch_result = await self._execute_step(task, fetch_step, budget)
                        if fetch_result is not None:
                            results.append(fetch_result)
                            if fetch_result.success:
                                fetched = fetch_result.data.get("evidence", [])
                                if isinstance(fetched, list):
                                    web_evidence_candidates.extend(fetched)

                # Re-evaluate and synthesize from the new evidence before any
                # further retrieval refinement. Budget limits bound this loop.
                continue

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

        required_source_classes = {
            TaskType.CORPORATE_KNOWLEDGE: {SourceClass.CORPORATE},
            TaskType.WEB_RESEARCH: {SourceClass.WEB},
            TaskType.CORPORATE_AND_WEB: {
                SourceClass.CORPORATE,
                SourceClass.WEB,
            },
        }.get(task.task_type, set())
        if task.task_type == TaskType.CORPORATE_KNOWLEDGE and any(
            item.success and item.capability == CapabilityType.WEB_SEARCH
            for item in results
        ):
            # INTERNAL_FIRST_WEB_FALLBACK may answer from public evidence when
            # corporate evidence is insufficient; it must then cite WEB.
            required_source_classes = {SourceClass.WEB}
        present_source_classes = {
            item.source_class for item in evaluation.applicable
        }
        missing_source_classes = required_source_classes - present_source_classes
        if missing_source_classes:
            missing_names = sorted(item.value for item in missing_source_classes)
            evaluation.status = EvidenceStatus.INSUFFICIENT_EVIDENCE
            conflict_errors.append(
                "REQUIRED_SOURCE_CLASS_MISSING:" + ",".join(missing_names)
            )
            synthesis = SynthesisResult(
                answer="",
                resolution=QuestionResolution.INSUFFICIENT,
                uncertainty="Required evidence source class is unavailable.",
            )

        verification = verify_evidence_support(
            claims=synthesis.material_claims,
            evidence=evaluation.applicable,
            citations=synthesis.evidence_ids,
            conflict_errors=conflict_errors,
        )

        semantic_results = []
        semantic_errors = []

        if (
            synthesis.resolution in (
                QuestionResolution.ANSWERABLE,
                QuestionResolution.CONFLICTED,
            )
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
