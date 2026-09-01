"""Hybrid sparse + dense retrieval utilities."""
from typing import List, Dict, Any
import re

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from config.settings import settings
from config.logging import logger


class HybridRetriever:
    """Combine BM25 lexical retrieval with cached dense embeddings."""

    def __init__(self, documents: List[Dict[str, Any]] | None = None, embedder=None):
        self.documents: List[Dict[str, Any]] = []
        self.embedder = embedder or SentenceTransformer(settings.EMBEDDING_MODEL)
        self.bm25 = None
        self.doc_embeddings = None
        self.index(documents or [])

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9+#.\-/]+", (text or "").lower())

    def _build_bm25(self, documents: List[Dict[str, Any]]):
        tokenized = [self._tokens(d.get("text", "")) for d in documents]
        return BM25Okapi(tokenized) if tokenized else None

    def index(self, documents: List[Dict[str, Any]]) -> None:
        """Build both sparse and dense indexes once for the supplied documents."""
        self.documents = list(documents)
        self.bm25 = self._build_bm25(self.documents)

        if not self.documents:
            self.doc_embeddings = None
            return

        texts = [d.get("text", "") for d in self.documents]
        self.doc_embeddings = self.embedder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        logger.info("Indexed %d documents for hybrid retrieval", len(self.documents))

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not self.documents or self.doc_embeddings is None:
            return []

        k = max(1, min(k, len(self.documents)))
        query_tokens = self._tokens(query)
        sparse = self.bm25.get_scores(query_tokens) if self.bm25 else []

        # Only the query is encoded at search time; document embeddings are cached.
        query_embedding = self.embedder.encode(query, normalize_embeddings=True, show_progress_bar=False)
        dense = self.doc_embeddings @ query_embedding

        ranked = []
        sparse_max = max(sparse) if len(sparse) else 0.0
        sparse_min = min(sparse) if len(sparse) else 0.0
        sparse_range = sparse_max - sparse_min or 1.0

        for i, doc in enumerate(self.documents):
            bm25_score = (float(sparse[i]) - sparse_min) / sparse_range if len(sparse) else 0.0
            dense_score = (float(dense[i]) + 1.0) / 2.0
            score = 0.45 * bm25_score + 0.55 * dense_score
            ranked.append((score, doc))

        ranked.sort(key=lambda x: x[0], reverse=True)
        logger.info("Hybrid retrieval returned %d/%d documents", min(k, len(ranked)), len(ranked))
        return [{**doc, "retrieval_score": round(score, 4)} for score, doc in ranked[:k]]
