"""In-memory BM25 index over each chunk's ``embed_text``, the same text the vectors come from (D7).

The index is rebuilt from the vector store on startup and after each ingest. It is not
persisted.
"""

import re

from rank_bm25 import BM25Okapi

TOKEN = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class BM25Index:
    """Keyword search over ``(chunk id, embed_text)`` pairs."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._terms: list[set[str]] = []
        self._index: BM25Okapi | None = None

    def build(self, pairs: list[tuple[str, str]]) -> None:
        """Replace the index with the given ``(chunk id, embed_text)`` pairs."""
        self._ids = [identifier for identifier, _ in pairs]
        corpus = [tokenize(text) for _, text in pairs]
        self._terms = [set(tokens) for tokens in corpus]
        self._index = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        """Return up to ``k`` chunk IDs with their scores, best first.

        Only chunks that share at least one word with the query are returned. BM25 scores
        can be negative in small corpora, so the score alone is not used as the filter.
        """
        if self._index is None:
            return []
        query_terms = set(tokenize(query))
        scores = self._index.get_scores(list(query_terms))
        ranked = sorted(zip(self._ids, scores, self._terms, strict=True), key=lambda row: -row[1])
        return [
            (identifier, float(score)) for identifier, score, terms in ranked if terms & query_terms
        ][:k]

    def __len__(self) -> int:
        return len(self._ids)
