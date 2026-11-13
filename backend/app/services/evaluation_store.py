from __future__ import annotations

from app.models.evaluation import EvaluationResult
from app.models.review import ReviewResult

_STORE: dict[str, EvaluationResult] = {}
_REVIEW_STORE: dict[str, ReviewResult] = {}


def save_evaluation(result: EvaluationResult) -> EvaluationResult:
    _STORE[result.id] = result
    return result


def get_evaluation(evaluation_id: str) -> EvaluationResult | None:
    return _STORE.get(evaluation_id)


def clear_evaluations() -> None:
    _STORE.clear()
    _REVIEW_STORE.clear()


def save_review(result: ReviewResult) -> ReviewResult:
    _REVIEW_STORE[result.id] = result
    return result


def get_review(review_id: str) -> ReviewResult | None:
    return _REVIEW_STORE.get(review_id)
