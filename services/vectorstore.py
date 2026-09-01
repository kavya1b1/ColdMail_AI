"""ChromaDB vector store with metadata-aware hybrid retrieval."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

from config.settings import settings
from config.logging import logger
from services.retrieval import HybridRetriever


class VectorStoreService:
    """Persist embeddings and expose metadata-filtered semantic/hybrid search."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR, settings=ChromaSettings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(name=settings.CHROMA_COLLECTION)
        self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)

    def _add(self, item_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        try:
            clean_metadata = {k: (str(v) if not isinstance(v, (str, int, float, bool)) else v) for k, v in metadata.items()}
            self.collection.upsert(
                ids=[item_id],
                embeddings=[self.embedder.encode(text, normalize_embeddings=True).tolist()],
                documents=[text],
                metadatas=[clean_metadata],
            )
            return True
        except Exception as exc:
            logger.error("Vector store write error: %s", exc)
            return False

    def add_company(self, company_id: str, company_data: Dict[str, Any]) -> bool:
        text = f"{company_data.get('name', '')} {company_data.get('description', '')} {company_data.get('industry', '')} {' '.join(company_data.get('tech_stack', []))}"
        return self._add(f"company_{company_id}", text, {**company_data, "record_type": "company"})

    def add_email(self, email_id: str, email_data: Dict[str, Any]) -> bool:
        text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
        return self._add(f"email_{email_id}", text, {**email_data, "record_type": "email"})

    def _search(self, query: str, n_results: int, record_type: str) -> List[Dict[str, Any]]:
        try:
            embedding = self.embedder.encode(query, normalize_embeddings=True).tolist()
            result = self.collection.query(query_embeddings=[embedding], n_results=n_results, where={"record_type": record_type})
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            return [{**item, "semantic_distance": distances[i] if i < len(distances) else None} for i, item in enumerate(metadatas)]
        except Exception as exc:
            logger.error("Vector search error: %s", exc)
            return []

    def search_similar_companies(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        return self._search(query, n_results, "company")

    def search_similar_emails(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        return self._search(query, n_results, "email")

    def get_relevant_context(self, company_name: str, skills: List[str]) -> str:
        """Use hybrid BM25+dense retrieval over prior emails."""
        try:
            raw = self.collection.get(where={"record_type": "email"}, include=["documents", "metadatas"])
            docs = []
            for text, metadata in zip(raw.get("documents", []), raw.get("metadatas", [])):
                docs.append({"text": text, "metadata": metadata or {}})
            results = HybridRetriever(docs).search(f"{company_name} {' '.join(skills)}", k=3)
            return "\n".join(f"Previous relevant email: {r['text'][:300]}" for r in results)
        except Exception as exc:
            logger.error("Hybrid context retrieval failed: %s", exc)
            return ""
