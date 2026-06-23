"""
Persistent Vector Store Wrapper using ChromaDB for caching and document retrieval.
Integrates with core/embeddings.py.
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Fallback in-memory cache if chromadb is not available or fails
_IN_MEMORY_STORE: Dict[str, Dict[str, List[float]]] = {
    "resume_embeddings": {},
    "jd_embeddings": {},
    "skill_vectors": {}
}

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    logger.warning("chromadb package is not installed. Falling back to in-memory embedding cache.")
    CHROMA_AVAILABLE = False

CHROMA_DIR = os.path.join("data", "chroma_db")

class VectorStoreManager:
    """Manages persistent ChromaDB collections with graceful fallbacks."""
    
    _client = None
    _collections = {}

    @classmethod
    def get_client(cls):
        """Lazy initializer for ChromaDB persistent client."""
        if not CHROMA_AVAILABLE:
            return None
        if cls._client is None:
            try:
                os.makedirs(CHROMA_DIR, exist_ok=True)
                cls._client = chromadb.PersistentClient(
                    path=CHROMA_DIR,
                    settings=Settings(anonymized_telemetry=False)
                )
                logger.info("ChromaDB PersistentClient initialized at %s", CHROMA_DIR)
            except Exception as e:
                logger.error("Failed to initialize ChromaDB. Falling back to in-memory. Error: %s", e)
                return None
        return cls._client

    @classmethod
    def get_collection(cls, name: str):
        """Retrieve or create a collection."""
        client = cls.get_client()
        if client is None:
            return None
        if name not in cls._collections:
            try:
                cls._collections[name] = client.get_or_create_collection(name=name)
            except Exception as e:
                logger.error("Failed to get/create ChromaDB collection '%s': %s", name, e)
                return None
        return cls._collections[name]

    @staticmethod
    def compute_sha256(text: str) -> str:
        """Compute SHA-256 hash of a string for deduplication/caching key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_cached_embedding(collection_name: str, text: str) -> Optional[List[float]]:
    """
    Retrieve cached embedding from ChromaDB if it exists.
    
    Parameters
    ----------
    collection_name: Name of the collection (resume_embeddings, jd_embeddings, skill_vectors)
    text: The input text to check
    """
    if not text or not text.strip():
        return None
    
    doc_id = VectorStoreManager.compute_sha256(text)
    
    # 1. Try ChromaDB
    collection = VectorStoreManager.get_collection(collection_name)
    if collection is not None:
        try:
            res = collection.get(ids=[doc_id], include=["embeddings"])
            if res and res.get("embeddings") and len(res["embeddings"]) > 0:
                logger.debug("Embedding cache hit in ChromaDB: %s", doc_id)
                return res["embeddings"][0]
        except Exception as e:
            logger.warning("Error reading from ChromaDB collection '%s': %s", collection_name, e)
    
    # 2. Try In-Memory Fallback
    if collection_name in _IN_MEMORY_STORE:
        return _IN_MEMORY_STORE[collection_name].get(doc_id)
    
    return None


def cache_embedding(collection_name: str, text: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
    """
    Cache an embedding in ChromaDB and/or in-memory fallback.
    """
    if not text or not text.strip() or not embedding:
        return
    
    doc_id = VectorStoreManager.compute_sha256(text)
    
    # 1. Save to ChromaDB
    collection = VectorStoreManager.get_collection(collection_name)
    if collection is not None:
        try:
            # Upsert into ChromaDB
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}]
            )
            logger.debug("Cached embedding in ChromaDB: %s", doc_id)
        except Exception as e:
            logger.warning("Failed to cache embedding in ChromaDB: %s", e)
            
    # 2. Save to In-Memory Fallback
    if collection_name in _IN_MEMORY_STORE:
        _IN_MEMORY_STORE[collection_name][doc_id] = embedding


def get_embedding_with_cache(collection_name: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[float]:
    """
    Get embedding for a text, checking the persistent cache first,
    computing if missing, and then storing in the cache.
    """
    cached = get_cached_embedding(collection_name, text)
    if cached is not None:
        return cached
    
    # Compute using existing core/embeddings.py
    from core.embeddings import get_single_embedding
    computed_arr = get_single_embedding(text)
    computed_list = computed_arr.tolist() if hasattr(computed_arr, "tolist") else list(computed_arr)
    
    # Store in cache
    cache_embedding(collection_name, text, computed_list, metadata)
    return computed_list
