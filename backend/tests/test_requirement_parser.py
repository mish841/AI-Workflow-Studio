import unittest

from app.ingestion.requirement_parser import (
    EXPECTED_REQUIREMENT_IDS,
    parse_reference_requirements,
)


class RequirementParserTest(unittest.TestCase):
    def test_parses_eighteen_unique_requirements(self):
        documents = parse_reference_requirements()

        self.assertEqual(len(documents), 18)
        ids = [doc.metadata["requirement_id"] for doc in documents]
        self.assertEqual(sorted(ids), sorted(EXPECTED_REQUIREMENT_IDS))
        self.assertEqual(len(set(ids)), 18)

        by_id = {doc.metadata["requirement_id"]: doc for doc in documents}

        ac01 = by_id["AC-01"]
        self.assertEqual(ac01.metadata["source_file"], "access_control_standard.txt")
        self.assertEqual(ac01.metadata["category"], "access_control")
        self.assertIn("Privileged user accounts must use multi-factor authentication.", ac01.page_content)
        self.assertTrue(ac01.page_content.startswith("AC-01"))

        auth02 = by_id["AUTH-02"]
        self.assertEqual(auth02.metadata["category"], "authentication")
        self.assertIn("14 characters", auth02.page_content)

        dp03 = by_id["DP-03"]
        self.assertEqual(dp03.metadata["source_file"], "data_protection_standard.txt")
        self.assertIn("12 months", dp03.page_content)

        ir01 = by_id["IR-01"]
        self.assertEqual(ir01.metadata["category"], "incident_response")
        self.assertIn("within one hour of detection", ir01.page_content)

        for document in documents:
            self.assertTrue(document.page_content.strip())
            self.assertIn(document.metadata["requirement_id"], document.page_content)


if __name__ == "__main__":
    unittest.main()
