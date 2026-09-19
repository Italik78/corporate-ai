from dataclasses import dataclass
from app.models import AnswerStatus

NO_ANSWER = "Няма достатъчно информация в предоставените документи."

@dataclass(frozen=True)
class PartialAnswerResult:
    status: AnswerStatus
    answer: str
    grounded: bool

class PartialAnswerEngine:
    def build(self, *, decision: dict, claims: list) -> PartialAnswerResult:
        answer = str(decision.get("answer", "") or "").strip()
        supported = [claim for claim in claims if getattr(claim, "supported", False)]
        unanswered_parts = [
            str(part).strip()
            for part in decision.get("unanswered_parts", [])
            if str(part).strip()
        ]

        if not supported:
            return PartialAnswerResult(AnswerStatus.NO_ANSWER, NO_ANSWER, False)
        if unanswered_parts:
            return PartialAnswerResult(AnswerStatus.PARTIAL, answer, False)
        return PartialAnswerResult(AnswerStatus.FULL, answer, True)
