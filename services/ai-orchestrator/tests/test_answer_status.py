from app.main import determine_answer_status
from app.models import (
    AnswerStatus,
    EvidenceStatus,
    QuestionResolution,
    TaskType,
    VerificationResult,
)


def test_conflict_status_requires_conflicted_evidence_and_passed_verification():
    assert determine_answer_status(
        task_type=TaskType.CORPORATE_AND_WEB,
        resolution=QuestionResolution.CONFLICTED,
        verification=VerificationResult(passed=True),
        evidence_status=EvidenceStatus.CONFLICT,
    ) == AnswerStatus.CONFLICT

    assert determine_answer_status(
        task_type=TaskType.CORPORATE_AND_WEB,
        resolution=QuestionResolution.CONFLICTED,
        verification=VerificationResult(passed=False),
        evidence_status=EvidenceStatus.CONFLICT,
    ) == AnswerStatus.NO_ANSWER

    assert determine_answer_status(
        task_type=TaskType.CORPORATE_AND_WEB,
        resolution=QuestionResolution.CONFLICTED,
        verification=VerificationResult(passed=True),
        evidence_status=EvidenceStatus.SUPPORTED,
    ) == AnswerStatus.NO_ANSWER
