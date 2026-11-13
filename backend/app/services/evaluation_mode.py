"""How the API chooses an evaluation method for user-facing assessments.

Product assessments request ``auto``. Engineering clients may still send
``direct`` or ``rag`` to force a method for tests and benchmarking.

Policy:

1. Prefer retrieved-passage evaluation (``rag``) when policy passages for
   the selected version are ingested and pass verification.
2. Do not silently fall back to full-document (``direct``) evaluation.
   Full-document fallback runs only when ``COMPLIANCE_ALLOW_DIRECT_FALLBACK``
   is ``true``, and the result records that fallback.
3. If retrieval is unavailable and fallback is not enabled, fail clearly.
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from fastapi import HTTPException

RequestedEvaluationMode = Literal["auto", "direct", "rag"]
ResolvedEvaluationMode = Literal["direct", "rag"]


def retrieval_is_ready() -> bool:
    from app.ingestion.ingest import verify_stored_policies

    try:
        return bool(verify_stored_policies()["ok"])
    except Exception:
        return False


def direct_fallback_enabled() -> bool:
    return os.getenv("COMPLIANCE_ALLOW_DIRECT_FALLBACK", "").lower() in {
        "1",
        "true",
        "yes",
    }


def resolve_evaluation_mode(
    requested: Optional[RequestedEvaluationMode] = "auto",
    *,
    rag_ready: Optional[bool] = None,
    allow_direct_fallback: Optional[bool] = None,
) -> dict:
    """Return the method to run plus metadata for the result record."""
    choice = requested or "auto"
    ready = retrieval_is_ready() if rag_ready is None else rag_ready
    fallback_ok = (
        direct_fallback_enabled()
        if allow_direct_fallback is None
        else allow_direct_fallback
    )

    if choice == "direct":
        return {
            "requested_mode": "direct",
            "evaluation_mode": "direct",
            "fallback_used": False,
            "retrieval_ready": ready,
        }

    if choice == "rag":
        if not ready:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Source passages for this policy are not available, so the "
                    "assessment cannot use retrieved evidence."
                ),
            )
        return {
            "requested_mode": "rag",
            "evaluation_mode": "rag",
            "fallback_used": False,
            "retrieval_ready": True,
        }

    if ready:
        return {
            "requested_mode": "auto",
            "evaluation_mode": "rag",
            "fallback_used": False,
            "retrieval_ready": True,
        }

    if fallback_ok:
        return {
            "requested_mode": "auto",
            "evaluation_mode": "direct",
            "fallback_used": True,
            "retrieval_ready": False,
        }

    raise HTTPException(
        status_code=503,
        detail=(
            "This assessment needs prepared source documents in the library. "
            "Ask an administrator to index the company policies, then try again."
        ),
    )
