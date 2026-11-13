from __future__ import annotations

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

TOKEN = re.compile(r"[a-z0-9]+")


class LexicalEmbeddings(Embeddings):
    """Deterministic bag-of-words vectors for tests. Not used in production.

    Tokens are hashed with SHA-256 so vectors are stable across processes
    (unlike Python's randomized ``hash()``).
    """

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _bucket(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN.findall(text.lower()):
            vector[self._bucket(token)] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class VocabEmbeddings(Embeddings):
    """One dimension per corpus token. Useful for in-memory ranking tests."""

    def __init__(self, texts: list[str]):
        vocab: set[str] = set()
        for text in texts:
            vocab.update(TOKEN.findall(text.lower()))
        self.index = {token: index for index, token in enumerate(sorted(vocab))}
        self.dimensions = max(len(self.index), 1)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN.findall(text.lower()):
            index = self.index.get(token)
            if index is not None:
                vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
