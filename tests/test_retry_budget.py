import pytest

from engine.pacing.budget import BudgetExhaustedError, BudgetTracker


def test_call_budget_enforced():
    b = BudgetTracker(max_inference_calls=2, max_retries_per_task=5)
    b.record_call()
    b.record_call()
    with pytest.raises(BudgetExhaustedError):
        b.record_call()


def test_retry_budget_per_task():
    b = BudgetTracker(max_inference_calls=100, max_retries_per_task=2)
    b.record_retry("T1")
    b.record_retry("T1")
    with pytest.raises(BudgetExhaustedError):
        b.record_retry("T1")
    b.record_retry("T2")  # other tasks unaffected


def test_call_and_retry_budgets_independent():
    b = BudgetTracker(max_inference_calls=1, max_retries_per_task=1)
    b.record_call()
    with pytest.raises(BudgetExhaustedError):
        b.record_call()
    b.record_retry("T1")  # retry budget still available independently
