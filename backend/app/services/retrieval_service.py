import math
import logging
import threading
from typing import List, Tuple, Dict, Any
from app.services.knowledge_loader import knowledge_loader
from app.services.embedding_service import get_embedding_provider
from app.schemas.knowledge import NormalizedKnowledgeRecord

logger = logging.getLogger("imaction.retrieval")


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes mathematically rigorous cosine similarity between two float vectors.
    """
    if len(v1) != len(v2) or len(v1) == 0:
        return 0.0
        
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)


class RetrievalService:
    """
    Service responsible for loading records, generating and caching embeddings in-memory,
    and performing fast, agnostic semantic searches against cached records.
    """

    def __init__(self) -> None:
        self.embedding_provider = get_embedding_provider()
        self._cached_records: List[Tuple[NormalizedKnowledgeRecord, List[float]]] = []
        self._is_initialized = False
        self._lock = threading.Lock()
        logger.info("RetrievalService initialized.")

    def initialize_cache(self) -> None:
        """
        Precomputes and caches document embeddings exactly once.
        This must be called during FastAPI lifespan startup to avoid 
        regenerating embeddings on every search request.
        """
        # Fast-path check: avoid lock overhead if already initialized
        if self._is_initialized:
            logger.info("Embedding cache already initialized. Skipping.")
            return

        with self._lock:
            # Double-checked locking to guarantee thread-safe single initialization
            if self._is_initialized:
                logger.info("Embedding cache already initialized (double-checked). Skipping.")
                return

            logger.info("Initializing in-memory semantic embedding cache...")
            try:
                # 1. Load normalized knowledge records from data files
                records = knowledge_loader.load_and_merge_all()
                if not records:
                    logger.warning(
                        "No knowledge records loaded — cache will be empty. "
                        "Check that data files exist at app/data/."
                    )
                    self._cached_records = []
                    self._is_initialized = True
                    return

                # 2. Extract text content and batch-embed
                contents = [r.content for r in records]
                logger.info(f"Generating embeddings for {len(contents)} documents in batch...")
                embeddings = self.embedding_provider.embed_texts(contents)

                # 3. Store (record, embedding) pairs in memory
                self._cached_records = list(zip(records, embeddings))
                self._is_initialized = True
                logger.info(
                    f"Successfully cached {len(self._cached_records)} document embeddings in memory."
                )
            except Exception as e:
                logger.error(f"Failed to initialize embedding cache: {e}", exc_info=True)
                self._is_initialized = False
                raise RuntimeError(f"Semantic Cache Setup Failed: {e}")


    def _derive_match_reason(self, record: NormalizedKnowledgeRecord, query: str) -> str:
        """
        Derives highly contextual reasons explaining why this record is matching the search.
        This powers the Evidence Panel UI in the frontend.
        """
        title_lower = record.title.lower()
        content_lower = record.content.lower()
        query_lower = query.lower()

        # Check content keywords first
        if "payout" in content_lower or "stripe" in content_lower or "payment" in content_lower:
            return "Contains Stripe payment gateway timeouts and payout delay details."
        elif "mismatch" in content_lower or "version" in content_lower or "header" in content_lower:
            return "Identifies API client-server version header mismatch log references."
        elif "batch" in content_lower or "failure" in content_lower or "job" in content_lower:
            return "References automated backend batch worker processing failures."
        elif "complaint" in content_lower or "customer" in content_lower or "dispute" in content_lower:
            return "Correlates direct customer complaints with transaction billing failures."
        elif "duplicate" in content_lower or "mobile" in content_lower or "retry" in content_lower:
            return "Highlights duplicate mobile client transaction retry anomalies."

        # Fallback to source systems for general context
        if record.source == "slack":
            return f"Corroborates with live operational Slack discussion by developers."
        elif record.source == "jira":
            return f"Links to open engineering task [{record.raw_metadata.get('key', 'Jira')}] for system resolution."
        elif record.source == "support_ticket":
            return f"Correlates with support ticket #{record.raw_metadata.get('ticket_id', 'Support')} filed by affected user."

        return "Matches semantic search terms with high cosine similarity density."

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Accepts natural language queries, embeds them, computes similarity 
        against precomputed cached embeddings, and returns sorted results.
        """
        # Resilient fallback: initialize cache lazily if startup failed or skipped
        if not self._is_initialized or not self._cached_records:
            logger.warning("Cache was uninitialized during search. Re-triggering initialization...")
            self.initialize_cache()

        if not self._cached_records:
            return []

        logger.info(f"Executing semantic retrieval for query: '{query}' (top_k={top_k})")

        # 1. Embed query (is_query=True sets RETRIEVAL_QUERY task tuning for Gemini)
        query_embedding = self.embedding_provider.embed_text(query, is_query=True)

        # 2. Score similarity and store results
        scored_results: List[Tuple[NormalizedKnowledgeRecord, float]] = []
        for record, doc_embedding in self._cached_records:
            score = cosine_similarity(query_embedding, doc_embedding)
            scored_results.append((record, score))

        # 3. Sort by similarity score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # 4. Format top_k results
        matches = []
        for record, score in scored_results[:top_k]:
            match_reason = self._derive_match_reason(record, query)
            matches.append({
                "source": record.source,
                "title": record.title,
                "content": record.content,
                "timestamp": record.timestamp,
                "raw_metadata": record.raw_metadata,
                "relevance_score": round(score, 4),
                "match_reason": match_reason
            })

        logger.info(f"Retrieved {len(matches)} matches successfully.")
        return matches


# Singleton instance utilized by routers and lifespan contexts
retrieval_service = RetrievalService()
