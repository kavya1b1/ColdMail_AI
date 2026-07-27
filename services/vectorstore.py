"""Production ChromaDB Vector Store Service"""
from __future__ import annotations
import hashlib

from typing import Any, Dict, List, Optional
import chromadb

from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from config.logging import logger

from config.settings import settings

class VectorStoreService:
    """
    Production vector store.

    Features
    --------
    • ChromaDB
    • SentenceTransformer embeddings
    • Embedding cache
    • Upserts
    • Metadata validation
    • Semantic search
    • RAG context
    • Health monitoring
    """

    DEFAULT_SEARCH_RESULTS = 5

    def __init__(self):

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False
            ),
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION
            )
        )

        self.embedder = SentenceTransformer(
            settings.EMBEDDING_MODEL
        )

        self.embedding_cache: Dict[
            str,
            List[float],
        ] = {}

        logger.info(
            "VectorStoreService initialized."
        )

    ####################################################################
    # Helpers
    ####################################################################

    def _hash(
        self,
        text: str,
    ) -> str:

        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    def _embed(
        self,
        text: str,
    ) -> List[float]:
        """
        Cached embeddings.
        """

        key = self._hash(text)

        cached = self.embedding_cache.get(
            key
        )

        if cached is not None:

            return cached

        embedding = (
            self.embedder
            .encode(text)
            .tolist()
        )

        self.embedding_cache[
            key
        ] = embedding

        return embedding

    ####################################################################
    # Metadata
    ####################################################################

    def _company_metadata(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "type": "company",
            "name": data.get("name") or "",
            "industry": data.get("industry") or "",
            "description": data.get("description") or "",
            "domain": data.get("domain") or "",
            "role": data.get("role") or "",
            "tech_stack": ", ".join(
                str(skill)
                for skill in (data.get("tech_stack") or [])
                if skill
            ),
        }

    def _email_metadata(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "type": "email",
            "recipient": data.get(
                "recipient_email",
                "",
            ),
            "subject": data.get(
                "subject",
                "",
            ),
            "quality": float(
                data.get(
                    "quality_score",
                    0,
                )
            ),
        }

    ####################################################################
    # Document Builders
    ####################################################################

    def _company_document(
        self,
        company: Dict[str, Any],
    ) -> str:

        tech_stack = company.get("tech_stack") or []

        parts = [
            company.get("name") or "",
            company.get("description") or "",
            company.get("industry") or "",
            company.get("role") or "",
            " ".join(
                str(skill)
                for skill in tech_stack
                if skill
            ),
        ]

        return "\n".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    def _email_document(
        self,
        email: Dict[str, Any],
    ) -> str:

        parts = [
            email.get("subject") or "",
            email.get("body") or "",
        ]

        return "\n".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    ####################################################################
    # Validation
    ####################################################################

    def _validate_id(
        self,
        item_id: str,
    ) -> bool:

        return bool(
            item_id and item_id.strip()
        )

    def _validate_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> bool:

        return (
            metadata is not None
            and isinstance(
                metadata,
                dict,
            )
        )
    
        ####################################################################
    # Company Storage
    ####################################################################

    def add_company(
        self,
        company_id: str,
        company_data: Dict[str, Any],
    ) -> bool:
        """
        Add or update a company in ChromaDB.
        """

        if not self._validate_id(company_id):
            return False

        metadata = self._company_metadata(
            company_data
        )

        if not self._validate_metadata(metadata):
            return False

        document = self._company_document(
            company_data
        )

        try:

            embedding = self._embed(
                document
            )

            self.collection.upsert(
                ids=[
                    f"company_{company_id}"
                ],
                embeddings=[
                    embedding
                ],
                documents=[
                    document
                ],
                metadatas=[
                    metadata
                ],
            )

            logger.info(
                "Stored company %s",
                company_id,
            )

            return True

        except Exception as exc:

            logger.exception(
                "Failed storing company %s: %s",
                company_id,
                exc,
            )

            return False

    ####################################################################
    # Email Storage
    ####################################################################

    def add_email(
        self,
        email_id: str,
        email_data: Dict[str, Any],
    ) -> bool:
        """
        Store a generated email.
        """

        if not self._validate_id(email_id):
            return False

        metadata = self._email_metadata(
            email_data
        )

        if not self._validate_metadata(metadata):
            return False

        document = self._email_document(
            email_data
        )

        try:

            embedding = self._embed(
                document
            )

            self.collection.upsert(
                ids=[
                    f"email_{email_id}"
                ],
                embeddings=[
                    embedding
                ],
                documents=[
                    document
                ],
                metadatas=[
                    metadata
                ],
            )

            logger.info(
                "Stored email %s",
                email_id,
            )

            return True

        except Exception as exc:

            logger.exception(
                "Failed storing email %s: %s",
                email_id,
                exc,
            )

            return False

    ####################################################################
    # Internal Search
    ####################################################################

    def _search(
        self,
        query: str,
        *,
        metadata_filter: Dict[str, Any],
        n_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Internal semantic search helper.
        """

        try:

            embedding = self._embed(
                query
            )

            results = self.collection.query(
                query_embeddings=[
                    embedding
                ],
                where=metadata_filter,
                n_results=n_results,
                include=[
                    "documents",
                    "metadatas",
                    "distances",
                ],
            )

            documents = results.get(
                "documents",
                [[]],
            )[0]

            metadatas = results.get(
                "metadatas",
                [[]],
            )[0]

            distances = results.get(
                "distances",
                [[]],
            )[0]

            output = []

            for document, metadata, distance in zip(
                documents,
                metadatas,
                distances,
            ):

                item = (
                    metadata.copy()
                    if metadata
                    else {}
                )

                item["document"] = document
                item["distance"] = distance

                output.append(
                    item
                )

            return output

        except Exception as exc:

            logger.exception(
                "Vector search failed: %s",
                exc,
            )

            return []

    ####################################################################
    # Company Search
    ####################################################################

    def search_similar_companies(
        self,
        query: str,
        n_results: int = DEFAULT_SEARCH_RESULTS,
    ) -> List[Dict[str, Any]]:
        """
        Search companies using semantic similarity.
        """

        return self._search(
            query,
            metadata_filter={
                "type": "company"
            },
            n_results=n_results,
        )

    ####################################################################
    # Email Search
    ####################################################################

    def search_similar_emails(
        self,
        query: str,
        n_results: int = DEFAULT_SEARCH_RESULTS,
    ) -> List[Dict[str, Any]]:
        """
        Search previous emails.
        """

        return self._search(
            query,
            metadata_filter={
                "type": "email"
            },
            n_results=n_results,
        )
    
        ####################################################################
    # RAG Context
    ####################################################################

    def get_relevant_context(
        self,
        company_name: str,
        skills: List[str],
        max_results: int = 3,
        max_chars: int = 1200,
    ) -> str:
        """
        Build RAG context for email generation.
        """

        query = (
            company_name
            + " "
            + " ".join(skills)
        ).strip()

        results = self.search_similar_emails(
            query=query,
            n_results=max_results,
        )

        if not results:
            return ""

        sections = []

        for idx, item in enumerate(results, start=1):

            body = (
                item.get("document", "")
                or ""
            )

            subject = item.get(
                "subject",
                "Previous Email",
            )

            distance = item.get(
                "distance",
                0,
            )

            section = (
                f"Example {idx}\n"
                f"Subject: {subject}\n"
                f"Similarity Distance: "
                f"{distance:.3f}\n"
                f"{body}"
            )

            sections.append(section)

        context = "\n\n".join(
            sections
        )

        if len(context) > max_chars:

            context = (
                context[:max_chars]
                + "\n..."
            )

        return context

    ####################################################################
    # Delete Operations
    ####################################################################

    def delete(
        self,
        item_id: str,
    ) -> bool:
        """
        Delete a vector by ID.
        """

        try:

            self.collection.delete(
                ids=[item_id]
            )

            logger.info(
                "Deleted %s",
                item_id,
            )

            return True

        except Exception as exc:

            logger.exception(
                "Delete failed: %s",
                exc,
            )

            return False

    ####################################################################
    # Collection Information
    ####################################################################

    def count(
        self,
    ) -> int:
        """
        Number of stored vectors.
        """

        try:

            return self.collection.count()

        except Exception:

            return 0

    ####################################################################
    # Cache
    ####################################################################

    def clear_embedding_cache(
        self,
    ):

        self.embedding_cache.clear()

        logger.info(
            "Embedding cache cleared."
        )

    ####################################################################
    # Statistics
    ####################################################################

    def statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Runtime statistics.
        """

        return {
            "documents": self.count(),
            "cached_embeddings": len(
                self.embedding_cache
            ),
            "embedding_model": settings.EMBEDDING_MODEL,
            "collection": settings.CHROMA_COLLECTION,
        }

    ####################################################################
    # Health
    ####################################################################

    def health(
        self,
    ) -> Dict[str, Any]:
        """
        Health information.
        """

        healthy = True
        try:

            self.collection.count()

        except Exception:

            healthy = False
        return {
            "service": "VectorStoreService",
            "status": (
                "healthy"
                if healthy
                else "unhealthy"
            ),
            "collection": settings.CHROMA_COLLECTION,
            "embedding_model": settings.EMBEDDING_MODEL,
            "documents": self.count(),
            "embedding_cache": len(
                self.embedding_cache
            ),
            "supports_upsert": True,
            "supports_rag": True,
            "supports_semantic_search": True,
        }


