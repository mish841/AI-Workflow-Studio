import unittest

from app.services.content_evaluator import evaluate_content
from app.services.project_qa_evaluator import evaluate_project_qa
from app.services.sox_evaluator import evaluate_sox
from app.workspaces.catalog import list_workspaces, load_workspace_documents


class SoxEvaluatorTest(unittest.TestCase):
    def setUp(self):
        self.result = evaluate_sox()
        self.by_id = {item.id: item for item in self.result.findings}

    def test_reviews_all_controls_across_three_dimensions(self):
        self.assertEqual(self.result.workspace, "sox")
        self.assertIn("not a sox audit opinion", self.result.disclaimer.lower())
        design = [item for item in self.result.findings if item.dimension == "design"]
        completeness = [
            item for item in self.result.findings if item.dimension == "completeness"
        ]
        operating = [
            item
            for item in self.result.findings
            if item.dimension == "operating_effectiveness"
        ]
        self.assertEqual(len(design), 11)
        self.assertEqual(len(completeness), 11)
        self.assertEqual(len(operating), 11)

    def test_known_defects(self):
        self.assertEqual(self.by_id["ITGC-01-O"].classification, "contradicted")
        self.assertIn("IAM-2240", self.by_id["ITGC-01-O"].evidence or "")
        self.assertEqual(self.by_id["ITGC-02-O"].classification, "contradicted")
        self.assertIn("Maya Chen", self.by_id["ITGC-02-O"].explanation)
        self.assertEqual(self.by_id["ITGC-03-O"].classification, "partial")
        self.assertEqual(self.by_id["ITGC-04-O"].classification, "satisfied")
        self.assertEqual(self.by_id["ITGC-05-O"].classification, "contradicted")
        self.assertEqual(self.by_id["ITGC-06-O"].classification, "missing")
        self.assertEqual(self.by_id["ITGC-07-O"].classification, "partial")
        self.assertEqual(self.by_id["ITGC-08-O"].classification, "contradicted")
        self.assertIn("Jordan Hale", self.by_id["ITGC-08-O"].explanation)
        self.assertEqual(self.by_id["ITGC-09-O"].classification, "partial")
        self.assertEqual(self.by_id["ITGC-10-O"].classification, "satisfied")
        self.assertEqual(self.by_id["ITGC-11-D"].classification, "partial")
        self.assertEqual(self.by_id["ITGC-11-O"].classification, "missing")

    def test_does_not_load_security_ground_truth(self):
        blob = " ".join(
            (item.explanation or "") + (item.evidence or "")
            for item in self.result.findings
        )
        self.assertNotIn("expected_status", blob)
        self.assertNotIn("expected_findings", blob)


class ProjectQaEvaluatorTest(unittest.TestCase):
    def setUp(self):
        self.by_id = {item.id: item for item in evaluate_project_qa().findings}

    def test_deterministic_rules(self):
        self.assertEqual(self.by_id["PQA-01"].classification, "missing")
        self.assertIn("RISK-04", self.by_id["PQA-01"].explanation)
        self.assertEqual(self.by_id["PQA-02"].classification, "contradicted")
        self.assertIn("ISSUE-02", self.by_id["PQA-02"].explanation)
        self.assertEqual(self.by_id["PQA-03"].classification, "missing")
        self.assertEqual(self.by_id["PQA-04"].classification, "missing")
        self.assertIn("UAT start", self.by_id["PQA-04"].explanation)
        self.assertEqual(self.by_id["PQA-05"].classification, "partial")
        self.assertIn("Budget", self.by_id["PQA-05"].explanation)
        self.assertEqual(self.by_id["PQA-06"].classification, "contradicted")
        self.assertIn("P-4400", self.by_id["PQA-06"].explanation)


class ContentEvaluatorTest(unittest.TestCase):
    def setUp(self):
        self.by_id = {item.id: item for item in evaluate_content().findings}

    def test_style_rules(self):
        self.assertEqual(self.by_id["CQ-01"].classification, "partial")
        self.assertIn("Owner", self.by_id["CQ-01"].explanation)
        self.assertEqual(self.by_id["CQ-02"].classification, "partial")
        self.assertIn("Contact", self.by_id["CQ-02"].explanation)
        self.assertEqual(self.by_id["CQ-03"].classification, "contradicted")
        self.assertIn("world-class", self.by_id["CQ-03"].explanation)
        self.assertEqual(self.by_id["CQ-04"].classification, "partial")


class WorkspaceCatalogTest(unittest.TestCase):
    def test_four_available_workspaces(self):
        ids = [item.id for item in list_workspaces()]
        self.assertEqual(ids, ["security", "sox", "project_qa", "content"])

    def test_sox_documents_include_catalog_and_evidence(self):
        docs = load_workspace_documents("sox")
        files = {doc.file for doc in docs}
        self.assertIn("controls.json", files)
        self.assertIn("joiners.json", files)
        self.assertEqual(len(docs), 9)


if __name__ == "__main__":
    unittest.main()
