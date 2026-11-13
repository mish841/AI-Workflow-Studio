import unittest

from app.ingestion.policy_chunker import chunk_policy_documents
from app.services.policy_loader import POLICY_FILES, POLICY_TITLES, load_policy_text


class PolicyChunkerTest(unittest.TestCase):
    def test_chunks_preserve_version_and_section_metadata(self):
        v1 = chunk_policy_documents(
            load_policy_text("v1"),
            policy_version="v1",
            filename=POLICY_FILES["v1"],
            title=POLICY_TITLES["v1"],
        )
        v2 = chunk_policy_documents(
            load_policy_text("v2"),
            policy_version="v2",
            filename=POLICY_FILES["v2"],
            title=POLICY_TITLES["v2"],
        )
        self.assertGreaterEqual(len(v1), 6)
        self.assertGreaterEqual(len(v2), 6)
        self.assertTrue(all(doc.metadata["policy_version"] == "v1" for doc in v1))
        self.assertTrue(all(doc.metadata["policy_version"] == "v2" for doc in v2))
        self.assertTrue(all(doc.metadata["chunk_id"].startswith("v1:") for doc in v1))
        self.assertTrue(all(doc.metadata["chunk_id"].startswith("v2:") for doc in v2))

        v1_text = "\n".join(doc.page_content for doc in v1)
        v2_text = "\n".join(doc.page_content for doc in v2)
        self.assertIn("thirty (30) days", v1_text)
        self.assertNotIn("twenty-four (24) hours", v1_text)
        self.assertIn("twenty-four (24) hours", v2_text)
        self.assertNotIn("thirty (30) days", v2_text)

        access = next(doc for doc in v1 if "Identities and access" in doc.metadata["section_title"])
        self.assertIn("unique user identifier", access.page_content)
        self.assertEqual(access.metadata["source_file"], "security_policy_v1.txt")


if __name__ == "__main__":
    unittest.main()
