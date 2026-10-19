"""Chunk IDs that depend only on content: the same chunk always gets the same ID."""

import hashlib

from rag_agent.ingestion.chunker import Chunk

FIELD_SEPARATOR = "\x1f"  # keeps "ab" + "c" and "a" + "bc" from hashing the same


def chunk_id(chunk: Chunk) -> str:
    """Return the SHA-256 of the chunk's source, heading path and text."""
    key = FIELD_SEPARATOR.join((chunk.source, chunk.heading_path, chunk.text))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
