import unittest
from pathlib import Path

from pydantic import ValidationError

from app.ingestion.requirement_parser import (
    EXPECTED_REQUIREMENT_IDS,
    parse_reference_requirements,
)
from app.models.evaluation import ComplianceFinding, ModelFinding
from app.services.compliance_evaluator import (
    SYSTEM_PROMPT,
    evaluate_policy,
    finalize_finding,
    inventory_from_documents,
    requirement_title,
)
from app.services.evidence import verify_quote
from app.services.evaluation_metrics import score_both_policies, score_findings
from app.services.ground_truth import expected_for_policy, load_expected_findings
from app.services.policy_loader import load_policy_text


POLICY_SNIPPET = (
    "Privileged users must sign in with multi-factor authentication. "
    "Password-only privileged access is not permitted.\n"
    "User passwords must be at least eight (8) characters."
)


def _requirement(requirement_id="AC-01", text="AC-01 Privileged MFA required."):
    from app.models.evaluation import RequirementSummary

    return RequirementSummary(
        requirement_id=requirement_id,
        title=requirement_title(text, requirement_id),
        category="access_control",
        source_file="access_control_standard.txt",
        text=text,
    )


class RequirementInventoryTest(unittest.TestCase):
    def test_inventory_contains_all_eighteen_requirements(self):
        documents = parse_reference_requirements()
        inventory = inventory_from_documents(documents)
        ids = [item.requirement_id for item in inventory]
        self.assertEqual(len(inventory), 18)
        self.assertEqual(sorted(ids), sorted(EXPECTED_REQUIREMENT_IDS))
        self.assertEqual(len(set(ids)), 18)
        for item in inventory:
            self.assertTrue(item.title)
            self.assertTrue(item.text.startswith(item.requirement_id))


class StructuredFindingTest(unittest.TestCase):
    def test_model_finding_requires_allowed_classification(self):
        finding = ModelFinding(
            requirement_id="AC-01",
            requirement_title="Privileged MFA",
            classification="satisfied",
            explanation="Policy requires MFA for privileged users.",
            supporting_quote="Privileged users must sign in with multi-factor authentication.",
        )
        self.assertEqual(finding.classification, "satisfied")
        with self.assertRaises(ValidationError):
            ModelFinding(
                requirement_id="AC-01",
                requirement_title="Privileged MFA",
                classification="unknown",
                explanation="bad",
            )


class EvidenceVerificationTest(unittest.TestCase):
    def test_exact_quote_is_verified(self):
        quote = "Privileged users must sign in with multi-factor authentication."
        self.assertEqual(verify_quote(quote, POLICY_SNIPPET), "verified")

    def test_missing_quote_is_missing(self):
        self.assertEqual(verify_quote(None, POLICY_SNIPPET), "missing")
        self.assertEqual(verify_quote("   ", POLICY_SNIPPET), "missing")

    def test_invented_quote_is_unverified(self):
        self.assertEqual(
            verify_quote("Quantum encryption is mandatory.", POLICY_SNIPPET),
            "unverified",
        )

    def test_real_v1_expected_quote_appears_in_policy(self):
        policy = load_policy_text("v1")
        expected = expected_for_policy("v1")["AC-01"]["expected_evidence"]
        self.assertEqual(verify_quote(expected, policy), "verified")


class FinalizeFindingTest(unittest.TestCase):
    def test_unverified_quote_flags_needs_review_without_forcing_missing(self):
        model = ModelFinding(
            requirement_id="AC-01",
            requirement_title="Privileged MFA",
            classification="satisfied",
            explanation="Claims a quote that is not in the policy.",
            supporting_quote="This sentence is not in the policy.",
        )
        finding = finalize_finding(
            _requirement(),
            model,
            POLICY_SNIPPET,
            "security_policy_v1.txt",
        )
        self.assertEqual(finding.classification, "satisfied")
        self.assertFalse(finding.evidence_verified)
        self.assertEqual(finding.evidence_verification, "unverified")
        self.assertTrue(finding.needs_review)
        self.assertEqual(finding.evaluation_state, "needs_review")

    def test_failed_evaluation_is_not_classified_as_missing(self):
        finding = finalize_finding(
            _requirement(),
            None,
            POLICY_SNIPPET,
            "security_policy_v1.txt",
            failed=True,
            failure_note="timeout",
        )
        self.assertIsNone(finding.classification)
        self.assertTrue(finding.needs_review)
        self.assertEqual(finding.evaluation_state, "failed")

    def test_prompt_does_not_include_ground_truth(self):
        from app.services.compliance_evaluator import RAG_SYSTEM_PROMPT

        for prompt in (SYSTEM_PROMPT, RAG_SYSTEM_PROMPT):
            self.assertNotIn("expected_findings", prompt)
            self.assertNotIn("expected_status", prompt)
            self.assertNotIn("ground truth", prompt.lower())


class EvaluatorWithMockedModelTest(unittest.TestCase):
    def test_evaluate_policy_uses_completer_and_source_filename(self):
        inventory = [_requirement("AC-01"), _requirement("AUTH-05", "AUTH-05 Password history.")]
        quotes = {
            "AC-01": "Privileged users must sign in with multi-factor authentication.",
            "AUTH-05": None,
        }

        def completer(requirement_id, requirement_text, policy_text, filename):
            self.assertEqual(filename, "security_policy_v1.txt")
            self.assertIn("multi-factor authentication", policy_text)
            self.assertNotIn("expected_status", policy_text)
            self.assertNotIn("expected_evidence", requirement_text)
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title=requirement_id,
                classification="satisfied" if quotes[requirement_id] else "missing",
                explanation="mocked",
                supporting_quote=quotes[requirement_id],
            )

        result = evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
        )
        self.assertEqual(len(result.findings), 2)
        by_id = {item.requirement_id: item for item in result.findings}
        self.assertTrue(by_id["AC-01"].evidence_verified)
        self.assertEqual(by_id["AUTH-05"].evidence_verification, "missing")
        self.assertEqual(by_id["AUTH-05"].classification, "missing")
        self.assertEqual(result.source_document, "security_policy_v1.txt")

    def test_per_requirement_failure_stays_needs_review(self):
        inventory = [_requirement("AC-01"), _requirement("AC-02", "AC-02 Access reviews.")]

        def completer(requirement_id, requirement_text, policy_text, filename):
            if requirement_id == "AC-02":
                raise RuntimeError("model exploded")
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title="Privileged MFA",
                classification="satisfied",
                explanation="ok",
                supporting_quote="Privileged users must sign in with multi-factor authentication.",
            )

        result = evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
        )
        by_id = {item.requirement_id: item for item in result.findings}
        self.assertEqual(by_id["AC-01"].evaluation_state, "completed")
        self.assertEqual(by_id["AC-02"].evaluation_state, "failed")
        self.assertIsNone(by_id["AC-02"].classification)

    def test_requirement_ids_limits_inventory_without_changing_default(self):
        inventory = [
            _requirement("AC-01"),
            _requirement("AC-03", "AC-03 Termination access revocation."),
        ]
        seen = []

        def completer(requirement_id, requirement_text, policy_text, filename):
            seen.append(requirement_id)
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title=requirement_id,
                classification="contradicted",
                explanation="mocked",
                supporting_quote="Privileged users must sign in with multi-factor authentication.",
            )

        result = evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
            requirement_ids=["AC-03"],
        )
        self.assertEqual(seen, ["AC-03"])
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].requirement_id, "AC-03")


class GroundTruthMetricsTest(unittest.TestCase):
    def test_perfect_mock_predictions_score_against_expected_labels(self):
        expected_v1 = expected_for_policy("v1")
        findings = [
            ComplianceFinding(
                requirement_id=requirement_id,
                requirement_title=requirement_id,
                requirement_text=requirement_id,
                classification=row["expected_status"],
                explanation=row["reason"],
                supporting_quote=row["expected_evidence"],
                source_document="security_policy_v1.txt",
                evidence_verified=row["expected_evidence"] is not None,
                evidence_verification="verified" if row["expected_evidence"] else "missing",
                needs_review=False,
                evaluation_state="completed",
            )
            for requirement_id, row in expected_v1.items()
        ]
        metrics = score_findings(findings, expected_v1)
        self.assertEqual(metrics.total_requirements_evaluated, 18)
        self.assertEqual(metrics.successful_classifications, 18)
        self.assertEqual(metrics.classification_accuracy, 1.0)
        self.assertEqual(metrics.per_status_expected.satisfied, 8)
        self.assertEqual(metrics.per_status_expected.partial, 5)
        self.assertEqual(metrics.per_status_expected.missing, 3)
        self.assertEqual(metrics.per_status_expected.contradicted, 2)
        self.assertIn("not a production accuracy claim", metrics.note)

    def test_thirty_six_labels_exist_across_both_policies(self):
        data = load_expected_findings()
        v1 = data["security_policy_v1"]
        v2 = data["security_policy_v2"]
        self.assertEqual(len(v1), 18)
        self.assertEqual(len(v2), 18)
        dummy = ComplianceFinding(
            requirement_id="AC-01",
            requirement_title="t",
            requirement_text="t",
            classification="satisfied",
            explanation="e",
            supporting_quote=None,
            source_document="security_policy_v1.txt",
            evidence_verified=False,
            evidence_verification="missing",
            needs_review=False,
            evaluation_state="completed",
        )
        v1_findings = [
            dummy.model_copy(
                update={
                    "requirement_id": requirement_id,
                    "classification": row["expected_status"],
                }
            )
            for requirement_id, row in v1.items()
        ]
        v2_findings = [
            dummy.model_copy(
                update={
                    "requirement_id": requirement_id,
                    "classification": row["expected_status"],
                }
            )
            for requirement_id, row in v2.items()
        ]
        combined = score_both_policies(v1_findings, v2_findings)
        self.assertEqual(combined.total_requirements_evaluated, 36)
        self.assertEqual(combined.classification_accuracy, 1.0)

    def test_failed_predictions_are_excluded_from_accuracy_denominator(self):
        expected = {"AC-01": {"expected_status": "satisfied"}}
        findings = [
            ComplianceFinding(
                requirement_id="AC-01",
                requirement_title="t",
                requirement_text="t",
                classification=None,
                explanation="failed",
                supporting_quote=None,
                source_document="security_policy_v1.txt",
                evidence_verified=False,
                evidence_verification="missing",
                needs_review=True,
                evaluation_state="failed",
            )
        ]
        metrics = score_findings(findings, expected)
        self.assertIsNone(metrics.classification_accuracy)
        self.assertEqual(metrics.successful_classifications, 0)
        self.assertEqual(metrics.failed_or_uncertain, 1)


class PromptIsolationTest(unittest.TestCase):
    def test_completer_never_receives_expected_findings_json(self):
        expected_path = (
            Path(__file__).resolve().parents[2]
            / "synthetic_data"
            / "evaluation"
            / "expected_findings.json"
        )
        forbidden = expected_path.read_text(encoding="utf-8")
        inventory = [_requirement()]

        def completer(requirement_id, requirement_text, policy_text, filename):
            blob = requirement_text + policy_text + filename + SYSTEM_PROMPT
            self.assertNotIn("expected_evidence", blob)
            self.assertNotIn('"expected_status"', blob)
            self.assertNotIn(forbidden[:80], blob)
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title="t",
                classification="missing",
                explanation="silent",
                supporting_quote=None,
            )

        evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
        )


class RagEvaluatorTest(unittest.TestCase):
    def test_rag_evaluates_full_inventory_even_when_retrieval_is_empty(self):
        inventory = [
            _requirement("AC-01"),
            _requirement("AC-03", "AC-03 Termination access revocation."),
        ]
        seen = []

        def completer(requirement_id, requirement_text, policy_text, filename):
            seen.append(requirement_id)
            self.assertIn("No policy passages were retrieved", policy_text)
            self.assertNotIn("expected_status", policy_text)
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title=requirement_id,
                classification="missing",
                explanation="no excerpts",
                supporting_quote=None,
                needs_review=True,
            )

        result = evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
            evaluation_mode="rag",
            passage_loader=lambda *args, **kwargs: [],
        )
        self.assertEqual(seen, ["AC-01", "AC-03"])
        self.assertEqual(result.evaluation_mode, "rag")
        self.assertEqual(len(result.findings), 2)
        for finding in result.findings:
            self.assertTrue(finding.needs_review)
            self.assertEqual(finding.evaluation_state, "needs_review")
            self.assertNotEqual(finding.evaluation_state, "failed")

    def test_retrieval_failure_is_needs_review_not_missing(self):
        inventory = [_requirement("AC-03", "AC-03 Termination access revocation.")]

        def boom(*args, **kwargs):
            raise RuntimeError("vector store down")

        result = evaluate_policy(
            "v1",
            completer=lambda *args, **kwargs: self.fail("model should not run"),
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
            evaluation_mode="rag",
            passage_loader=boom,
        )
        finding = result.findings[0]
        self.assertIsNone(finding.classification)
        self.assertEqual(finding.evaluation_state, "failed")
        self.assertTrue(finding.needs_review)

    def test_rag_context_is_retrieved_passages_and_quote_is_checked_against_source(self):
        from app.models.evaluation import RetrievedPassage

        inventory = [_requirement("AC-01")]
        passage = RetrievedPassage(
            chunk_id="v1:2-identities",
            source_document="security_policy_v1.txt",
            policy_version="v1",
            section_number="2",
            section_title="Identities and access",
            text="Privileged users must sign in with multi-factor authentication.",
            distance=0.1,
        )
        captured = {}

        def completer(requirement_id, requirement_text, policy_text, filename):
            captured["policy_text"] = policy_text
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title="Privileged MFA",
                classification="satisfied",
                explanation="MFA required",
                supporting_quote="Privileged users must sign in with multi-factor authentication.",
            )

        result = evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
            evaluation_mode="rag",
            passage_loader=lambda *args, **kwargs: [passage],
        )
        self.assertIn("[Passage 1", captured["policy_text"])
        self.assertNotIn("Password-only privileged access is not permitted.", captured["policy_text"])
        finding = result.findings[0]
        self.assertTrue(finding.evidence_verified)
        self.assertTrue(finding.retrieved_passages[0].used_in_finding)

    def test_direct_mode_still_sends_full_policy(self):
        inventory = [_requirement("AC-01")]
        captured = {}

        def completer(requirement_id, requirement_text, policy_text, filename):
            captured["policy_text"] = policy_text
            return ModelFinding(
                requirement_id=requirement_id,
                requirement_title="t",
                classification="satisfied",
                explanation="ok",
                supporting_quote="Privileged users must sign in with multi-factor authentication.",
            )

        evaluate_policy(
            "v1",
            completer=completer,
            inventory=inventory,
            policy_text=POLICY_SNIPPET,
            evaluation_mode="direct",
        )
        self.assertEqual(captured["policy_text"], POLICY_SNIPPET)


if __name__ == "__main__":
    unittest.main()
