from __future__ import annotations

from typing import Literal, Optional

EvidenceVerification = Literal["verified", "missing", "unverified"]


def verify_quote(quote: Optional[str], policy_text: str) -> EvidenceVerification:
    """Deterministic substring check against the original policy text.

    Exact matching is intentional for this baseline. The model must copy a
    quote from the policy; we do not fuzzy-match or invent evidence.
    """
    if quote is None:
        return "missing"
    stripped = quote.strip()
    if not stripped:
        return "missing"
    if stripped in policy_text:
        return "verified"
    return "unverified"
