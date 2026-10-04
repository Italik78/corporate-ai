import pytest

from app.budgets import BudgetController, BudgetExceeded
from app.models import Budget


def test_web_search_budget_is_enforced():
    controller = BudgetController(
        Budget(max_web_searches=1)
    )

    controller.consume_web_search()

    with pytest.raises(BudgetExceeded, match="max_web_searches exceeded"):
        controller.consume_web_search()


def test_web_fetch_budget_is_enforced():
    controller = BudgetController(
        Budget(max_web_fetches=1)
    )

    controller.consume_web_fetch()

    with pytest.raises(BudgetExceeded, match="max_web_fetches exceeded"):
        controller.consume_web_fetch()
