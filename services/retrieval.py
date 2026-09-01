"""Hybrid sparse + dense retrieval utilities."""
from typing import List, Dict, Any
import re

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from config.settings import settings
from config.logging import logger


class HybridRetriever:
    """Combine BM25 lexical retrieval with sentence-transformer similarity."""

    def __init__(self, documents: List[Dict[str, Any]] | None = None):
        self.documents = documents or []
        self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.bm25 = self._build_bm25(self.documents)

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9+#.\-/]+", (text or "").lower())

    def _build_bm25(self, documents: List[Dict[str, Any]]):
        return BM25Okapi([self._tokens(d.get("text", "")) for d in documents]) if documents else None

    def index(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents
        self.bm25 = self._build_bm25(documents)

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not self.documents:
            return []

        k = max(1, min(k, len(self.documents)))
        query_tokens = self._tokens(query)
        sparse = self.bm25.get_scores(query_tokens) if self.bm25 else []

        texts = [d.get("text", "") for d in self.documents]
        query_embedding = self.embedder.encode(query, normalize_embeddings=True)
        doc_embeddings = self.embedder.encode(texts, normalize_embeddings=True)
        dense = doc_embeddings @ query_embedding

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
