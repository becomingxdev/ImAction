import os
import random
import logging
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings

logger = logging.getLogger("imaction.embeddings")


class BaseEmbeddingProvider(ABC):
    """
    Abstract Base Class for Embedding Providers.
    Defines the contract for creating single and batch text embeddings.
    """

    @abstractmethod
    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        """
        Generates embedding representation for a single text payload.
        
        Args:
            text: Input string content.
            is_query: If True, uses Query task tuning. If False, uses Document task tuning.
        """
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embedding representations for a list of text documents in batch.
        """
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic Offline Local Embedding Provider.
    Generates deterministic, unit-normalized float vectors using basic hashing.
    Used for local developer testing and offline prototype verification.
    """

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension
        logger.info(f"Initialized MockEmbeddingProvider with dimension={self.dimension}")

    def _generate_deterministic_vector(self, text: str) -> List[float]:
        """
        Generates a unit-normalized vector where identical strings yield identical outputs.
        """
        if not text:
            return [0.0] * self.dimension
            
        # Unique deterministic seed based on text content
        seed = sum(ord(c) for c in text)
        rng = random.Random(seed)
        
        # Populate random array values
        raw_vals = [rng.uniform(-1, 1) for _ in range(self.dimension)]
        
        # Unit normalization (L2 norm) to ensure accurate cosine similarity computations
        norm = sum(x * x for x in raw_vals) ** 0.5
        if norm == 0:
            return [0.0] * self.dimension
            
        return [x / norm for x in raw_vals]

    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        return self._generate_deterministic_vector(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_deterministic_vector(t) for t in texts]


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Production Google Gemini and Vertex AI Embedding Provider.
    Wraps the official google-genai SDK, supporting both explicit API keys
    and local pre-authenticated Vertex AI service backends.
    """

    def __init__(self) -> None:
        from app.core.gemini_client import get_shared_gemini_client
        try:
            self.client = get_shared_gemini_client()
        except Exception as e:
            logger.critical(f"Failed to fetch shared google-genai Client: {e}", exc_info=True)
            raise RuntimeError(f"Embedding Provider client setup failed: {e}")

    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        from google.genai import types
        
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type)
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
            raise ValueError("Zero embeddings returned from GenAI service.")
        except Exception as e:
            logger.error(f"Failed to generate single text embedding via Gemini: {e}", exc_info=True)
            raise RuntimeError(f"Gemini Embedding Generation Error: {e}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        from google.genai import types
        
        if not texts:
            return []
            
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            if response.embeddings and len(response.embeddings) == len(texts):
                return [emb.values for emb in response.embeddings]
            raise ValueError(
                f"Batch embedding size mismatch. Expected {len(texts)}, "
                f"got {len(response.embeddings) if response.embeddings else 0}"
            )
        except Exception as e:
            logger.error(f"Failed to batch-generate text embeddings via Gemini: {e}", exc_info=True)
            raise RuntimeError(f"Gemini Batch Embedding Generation Error: {e}")


# ==============================================================================
# Singleton Provider Instance & Factory
# ==============================================================================
_embedding_provider_instance: BaseEmbeddingProvider = None


def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    Singleton factory function returning the configured BaseEmbeddingProvider.
    """
    global _embedding_provider_instance
    if _embedding_provider_instance is None:
        provider_type = settings.EMBEDDING_PROVIDER.lower().strip()
        if provider_type == "gemini":
            _embedding_provider_instance = GeminiEmbeddingProvider()
        else:
            _embedding_provider_instance = MockEmbeddingProvider()
            
    return _embedding_provider_instance
