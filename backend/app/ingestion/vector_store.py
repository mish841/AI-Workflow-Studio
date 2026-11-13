from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import text

from app.database import DATABASE_URL, engine

load_dotenv()

REQUIREMENT_COLLECTION = "compliance_requirements"
POLICY_COLLECTION = "policy_passages"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def pgvector_connection_string() -> str:
    """Derive a psycopg3 URL for langchain-postgres from DATABASE_URL.

    The FastAPI app keeps using psycopg2 via SQLAlchemy. langchain-postgres
    requires the psycopg3 driver name ``postgresql+psycopg://``.
    """
    url = DATABASE_URL
    replacements = (
        ("postgresql+psycopg2://", "postgresql+psycopg://"),
        ("postgresql://", "postgresql+psycopg://"),
        ("postgres://", "postgresql+psycopg://"),
    )
    for prefix, replacement in replacements:
        if url.startswith(prefix):
            return replacement + url[len(prefix) :]
    return url


def ensure_pgvector_extension() -> None:
    """Enable pgvector in the existing database using the app's SQLAlchemy engine."""
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def get_embeddings() -> Embeddings:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=api_key)


def get_vector_store(
    collection_name: str = REQUIREMENT_COLLECTION,
    embeddings: Optional[Embeddings] = None,
    *,
    pre_delete_collection: bool = False,
) -> PGVector:
    ensure_pgvector_extension()
    return PGVector(
        embeddings=embeddings or get_embeddings(),
        collection_name=collection_name,
        connection=pgvector_connection_string(),
        use_jsonb=True,
        create_extension=True,
        pre_delete_collection=pre_delete_collection,
    )
