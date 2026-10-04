from app.retrieval_strategy import diversify_candidates


def test_diversify_candidates_limits_chunks_per_document():
    candidates = [
        {"document_id": "doc-a", "chunk_id": f"a-{i}", "score": 1.0 - i * 0.01}
        for i in range(5)
    ] + [
        {"document_id": "doc-b", "chunk_id": f"b-{i}", "score": 0.90 - i * 0.01}
        for i in range(5)
    ] + [
        {"document_id": "doc-c", "chunk_id": f"c-{i}", "score": 0.80 - i * 0.01}
        for i in range(5)
    ]

    result = diversify_candidates(
        candidates,
        max_chunks_per_document=2,
        max_documents=3,
    )

    assert len(result) == 6
    assert [item["document_id"] for item in result].count("doc-a") == 2
    assert [item["document_id"] for item in result].count("doc-b") == 2
    assert [item["document_id"] for item in result].count("doc-c") == 2


def test_diversify_candidates_ignores_missing_document_id():
    candidates = [
        {"document_id": None, "chunk_id": "invalid", "score": 1.0},
        {"document_id": "", "chunk_id": "invalid-2", "score": 0.99},
        {"document_id": "doc-a", "chunk_id": "a-1", "score": 0.90},
    ]

    result = diversify_candidates(
        candidates,
        max_chunks_per_document=2,
        max_documents=3,
    )

    assert [item["chunk_id"] for item in result] == ["a-1"]


def test_diversify_candidates_accepts_realistic_retrieval_limits():
    candidates = [
        {"document_id": "doc-a", "chunk_id": "a-1", "score": 0.90},
        {"document_id": "doc-a", "chunk_id": "a-2", "score": 0.89},
        {"document_id": "doc-a", "chunk_id": "a-3", "score": 0.88},
        {"document_id": "doc-b", "chunk_id": "b-1", "score": 0.87},
        {"document_id": "doc-c", "chunk_id": "c-1", "score": 0.86},
    ]

    result = diversify_candidates(
        candidates,
        max_chunks_per_document=2,
        max_documents=2,
    )

    assert [item["chunk_id"] for item in result] == ["a-1", "a-2", "b-1"]


def test_default_retrieval_strategy_is_scalable():
    from app.retrieval_strategy import RetrievalStrategy

    strategy = RetrievalStrategy()

    assert strategy.candidate_limit == 50
    assert strategy.max_documents == 20
    assert strategy.max_chunks_per_document == 2
    assert strategy.score_threshold == 0.45


def test_corporate_plan_uses_scalable_retrieval_defaults():
    from app.models import SourceClass, Task, TaskType
    from app.planner import build_plan

    task = Task(
        user_request="Какъв е срокът по договора?",
        normalized_question="Какъв е срокът по договора?",
        task_type=TaskType.CORPORATE_KNOWLEDGE,
        allowed_source_classes=[SourceClass.CORPORATE],
    )

    plan = build_plan(task)

    assert len(plan.steps) == 1
    retrieval_input = plan.steps[0].input

    assert retrieval_input["candidate_limit"] == 50
    assert retrieval_input["max_documents"] == 20
    assert retrieval_input["max_chunks_per_document"] == 2
    assert retrieval_input["score_threshold"] == 0.45
