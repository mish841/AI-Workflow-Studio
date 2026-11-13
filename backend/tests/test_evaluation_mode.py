import unittest

from fastapi import HTTPException

from app.services.evaluation_mode import resolve_evaluation_mode


class ResolveEvaluationModeTest(unittest.TestCase):
    def test_auto_prefers_retrieved_passages_when_ready(self):
        resolved = resolve_evaluation_mode("auto", rag_ready=True, allow_direct_fallback=False)
        self.assertEqual(resolved["evaluation_mode"], "rag")
        self.assertFalse(resolved["fallback_used"])
        self.assertEqual(resolved["requested_mode"], "auto")

    def test_auto_errors_when_retrieval_unavailable_and_fallback_disabled(self):
        with self.assertRaises(HTTPException) as raised:
            resolve_evaluation_mode("auto", rag_ready=False, allow_direct_fallback=False)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("pgvector", str(raised.exception.detail).lower())
        self.assertNotIn("langchain", str(raised.exception.detail).lower())

    def test_auto_records_direct_fallback_when_enabled(self):
        resolved = resolve_evaluation_mode("auto", rag_ready=False, allow_direct_fallback=True)
        self.assertEqual(resolved["evaluation_mode"], "direct")
        self.assertTrue(resolved["fallback_used"])

    def test_explicit_direct_stays_direct(self):
        resolved = resolve_evaluation_mode("direct", rag_ready=False, allow_direct_fallback=False)
        self.assertEqual(resolved["evaluation_mode"], "direct")
        self.assertFalse(resolved["fallback_used"])

    def test_explicit_rag_errors_when_not_ready(self):
        with self.assertRaises(HTTPException):
            resolve_evaluation_mode("rag", rag_ready=False, allow_direct_fallback=True)


if __name__ == "__main__":
    unittest.main()
