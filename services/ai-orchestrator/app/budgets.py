from __future__ import annotations

from pydantic import BaseModel

from .models import Budget


def clamp_budget(requested: Budget, maximum: Budget | None = None) -> Budget:
    """Clients may lower work budgets, never raise server configured limits."""
    maximum = maximum or Budget()
    return Budget(**{
        field: min(getattr(requested, field), getattr(maximum, field))
        for field in Budget.model_fields
    })


class BudgetUsage(BaseModel):
    steps: int = 0
    capability_calls: int = 0
    retrieval_rounds: int = 0
    web_searches: int = 0
    web_fetches: int = 0
    verification_rounds: int = 0
    context_chars: int = 0


class BudgetExceeded(Exception):
    pass


class BudgetController:
    def __init__(self, budget: Budget):
        self.budget = budget
        self.usage = BudgetUsage()

    def consume_step(self) -> None:
        if self.usage.steps >= self.budget.max_steps:
            raise BudgetExceeded("max_steps exceeded")
        self.usage.steps += 1

    def consume_capability_call(self) -> None:
        if self.usage.capability_calls >= self.budget.max_capability_calls:
            raise BudgetExceeded("max_capability_calls exceeded")
        self.usage.capability_calls += 1

    def consume_retrieval_round(self) -> None:
        if self.usage.retrieval_rounds >= self.budget.max_retrieval_rounds:
            raise BudgetExceeded("max_retrieval_rounds exceeded")
        self.usage.retrieval_rounds += 1

    def consume_web_search(self) -> None:
        if self.usage.web_searches >= self.budget.max_web_searches:
            raise BudgetExceeded("max_web_searches exceeded")
        self.usage.web_searches += 1

    def consume_web_fetch(self) -> None:
        if self.usage.web_fetches >= self.budget.max_web_fetches:
            raise BudgetExceeded("max_web_fetches exceeded")
        self.usage.web_fetches += 1

    def consume_verification_round(self) -> None:
        if self.usage.verification_rounds >= self.budget.max_verification_rounds:
            raise BudgetExceeded("max_verification_rounds exceeded")
        self.usage.verification_rounds += 1

    def consume_context(self, chars: int) -> None:
        if chars < 0:
            raise ValueError("chars must be non-negative")
        if self.usage.context_chars + chars > self.budget.max_context_chars:
            raise BudgetExceeded("max_context_chars exceeded")
        self.usage.context_chars += chars
