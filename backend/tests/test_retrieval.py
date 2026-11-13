from __future__ import annotations

import unittest
import uuid

from langchain_core.documents import Document

from app.ingestion.ingest import (
    ingest_policies,
    ingest_requirements,
    verify_stored_policies,
    verify_stored_requirements,
)
from app.ingestion.requirement_parser import parse_reference_requirements
from app.services.retrieval import search_policy_passages, search_requirements
from app.services.retrieval_eval import evaluate_requirement_queries
from lexical_embeddings import LexicalEmbeddings, VocabEmbeddings


def _in_memory_search(documents: list[Document], embeddings: LexicalEmbeddings):
    vectors = embeddings.embed_documents([doc.page_content for doc in documents])

    def search(query: str, k: int, metadata_filter: dict | None):
        query_vec = embeddings.embed_query(query)
        scored = []
        for document, vector in zip(documents, vectors):
            metadata = document.metadata or {}
            if metadata_filter:
                if any(metadata.get(key) != value for key, value in metadata_filter.items()):
                    continue
            score = sum(a * b for a, b in zip(query_vec, vector))
            scored.append((document, 1.0 - score))
        scored.sort(key=lambda item: item[1])
        return scored[:k]

    return search


class RequirementRetrievalTest(unittest.TestCase):
    def test_termination_queries_retrieve_ac03(self):
        documents = parse_reference_requirements()
        embeddings = VocabEmbeddings([doc.page_content for doc in documents])
        search = _in_memory_search(documents, embeddings)
        for query in (
            "employee termination access revocation",
            "when a contractor engagement ends",
            "revocation after employment termination",
        ):
            hits = search_requirements(query, k=5, search=search)
            ids = [hit.metadata.get("requirement_id") or hit.id for hit in hits]
            self.assertIn("AC-03", ids, msg=f"{query} -> {ids}")
            self.assertEqual(ids[0], "AC-03", msg=f"{query} ranked {ids}")

    def test_independent_query_set_hits_ac03(self):
        documents = parse_reference_requirements()
        embeddings = VocabEmbeddings([doc.page_content for doc in documents])
        search = _in_memory_search(documents, embeddings)
        score = evaluate_requirement_queries(k=5, search=search)
        termination = [row for row in score["rows"] if row["id"].startswith("term-")]
        self.assertTrue(termination)
        self.assertTrue(all(row["hit"] for row in termination))
        self.assertGreaterEqual(score["hit_rate"], 0.5)


class PolicyRetrievalTest(unittest.TestCase):
    def test_policy_search_does_not_mix_versions(self):
        from app.ingestion.policy_chunker import chunk_policy_documents
        from app.services.policy_loader import POLICY_FILES, POLICY_TITLES, load_policy_text

        embeddings = LexicalEmbeddings()
        documents = []
        for version in ("v1", "v2"):
            documents.extend(
                chunk_policy_documents(
                    load_policy_text(version),
                    policy_version=version,
                    filename=POLICY_FILES[version],
                    title=POLICY_TITLES[version],
                )
            )
        search = _in_memory_search(documents, embeddings)
        query = "revoke access after employment termination"
        v1_hits = search_policy_passages(query, "v1", k=4, search=search)
        v2_hits = search_policy_passages(query, "v2", k=4, search=search)
        self.assertTrue(v1_hits)
        self.assertTrue(v2_hits)
        self.assertTrue(all(hit.metadata["policy_version"] == "v1" for hit in v1_hits))
        self.assertTrue(all(hit.metadata["policy_version"] == "v2" for hit in v2_hits))
        v1_text = "\n".join(hit.text for hit in v1_hits)
        v2_text = "\n".join(hit.text for hit in v2_hits)
        self.assertNotIn("twenty-four (24) hours", v1_text)
        self.assertNotIn("thirty (30) days", v2_text)


class PgvectorIngestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.embeddings = LexicalEmbeddings()
        cls.req_collection = f"test_req_{uuid.uuid4().hex[:8]}"
        cls.policy_collection = f"test_pol_{uuid.uuid4().hex[:8]}"
        ingest_requirements(
            embeddings=cls.embeddings,
            collection_name=cls.req_collection,
        )
        ingest_policies(
            embeddings=cls.embeddings,
            collection_name=cls.policy_collection,
        )

    def test_eighteen_requirements_ingested_with_metadata(self):
        result = verify_stored_requirements(self.req_collection)
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["count"], 18)
        ac03 = next(row for row in result["rows"] if row["id"] == "AC-03")
        self.assertEqual(ac03["metadata"]["requirement_id"], "AC-03")
        self.assertEqual(ac03["metadata"]["source_file"], "access_control_standard.txt")
        self.assertEqual(ac03["metadata"]["category"], "access_control")

    def test_requirement_ingest_is_idempotent(self):
        ingest_requirements(
            embeddings=self.embeddings,
            collection_name=self.req_collection,
        )
        result = verify_stored_requirements(self.req_collection)
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["count"], 18)

    def test_policy_ingest_keeps_versions_separate(self):
        result = verify_stored_policies(self.policy_collection)
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["versions"], ["v1", "v2"])

    def test_pgvector_termination_search_returns_ac03(self):
        hits = search_requirements(
            "employee termination access revocation",
            k=5,
            embeddings=self.embeddings,
            collection_name=self.req_collection,
        )
        ids = [hit.metadata.get("requirement_id") or hit.id.split(":")[-1] for hit in hits]
        self.assertEqual(ids[0], "AC-03")


if __name__ == "__main__":
    unittest.main()
