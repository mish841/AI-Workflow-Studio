from __future__ import annotations

from app.models.evaluation import (
    ComplianceFinding,
    EvaluationMetrics,
    PolicyVersion,
    StatusBreakdown,
)
from app.services.ground_truth import expected_for_policy, load_expected_findings

DATASET_NOTE = (
    "Accuracy is measured against a 36-label synthetic Northstar dataset "
    "(18 requirements × Policy V1 and V2). It is not a production accuracy claim."
)


def _empty_breakdown() -> StatusBreakdown:
    return StatusBreakdown()


def _count_predicted(findings: list[ComplianceFinding]) -> StatusBreakdown:
    counts = _empty_breakdown()
    for finding in findings:
        if finding.classification is None:
            counts.unlabeled += 1
        else:
            setattr(counts, finding.classification, getattr(counts, finding.classification) + 1)
    return counts


def _count_expected(expected: dict[str, dict]) -> StatusBreakdown:
    counts = _empty_breakdown()
    for row in expected.values():
        status = row["expected_status"]
        setattr(counts, status, getattr(counts, status) + 1)
    return counts


def score_findings(
    findings: list[ComplianceFinding],
    expected: dict[str, dict],
) -> EvaluationMetrics:
    comparable = [
        finding
        for finding in findings
        if finding.evaluation_state != "failed" and finding.classification is not None
    ]
    matches = 0
    for finding in comparable:
        expected_row = expected.get(finding.requirement_id)
        if expected_row and finding.classification == expected_row["expected_status"]:
            matches += 1

    verified = sum(1 for finding in findings if finding.evidence_verified)
    failed_or_uncertain = sum(
        1
        for finding in findings
        if finding.evaluation_state in {"failed", "needs_review"} or finding.needs_review
    )
    accuracy = (matches / len(comparable)) if comparable else None

    return EvaluationMetrics(
        total_requirements_evaluated=len(findings),
        successful_classifications=len(comparable),
        classification_accuracy=accuracy,
        per_status_predicted=_count_predicted(findings),
        per_status_expected=_count_expected(expected),
        evidence_verification_pass_rate=(verified / len(findings)) if findings else 0.0,
        failed_or_uncertain=failed_or_uncertain,
        note=DATASET_NOTE,
    )


def score_policy_evaluation(
    findings: list[ComplianceFinding],
    policy_version: PolicyVersion,
) -> EvaluationMetrics:
    return score_findings(findings, expected_for_policy(policy_version))


def score_both_policies(
    v1_findings: list[ComplianceFinding],
    v2_findings: list[ComplianceFinding],
) -> EvaluationMetrics:
    """Combine V1 and V2 predictions against all 36 expected labels."""
    expected = load_expected_findings()
    combined_expected: dict[str, dict] = {}
    combined_findings: list[ComplianceFinding] = []
    for finding in v1_findings:
        key = f"v1:{finding.requirement_id}"
        combined_expected[key] = expected["security_policy_v1"][finding.requirement_id]
        combined_findings.append(finding.model_copy(update={"requirement_id": key}))
    for finding in v2_findings:
        key = f"v2:{finding.requirement_id}"
        combined_expected[key] = expected["security_policy_v2"][finding.requirement_id]
        combined_findings.append(finding.model_copy(update={"requirement_id": key}))
    return score_findings(combined_findings, combined_expected)
