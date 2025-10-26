# vector_store.py
import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import hashlib
import json
from collections import OrderedDict

class SimpleLRUCache:
    def __init__(self, capacity=128):
        self.capacity = capacity
        self.data = OrderedDict()
    def get(self, key):
        if key in self.data:
            self.data.move_to_end(key)
            return self.data[key]
        return None
    def set(self, key, value):
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)

class VectorStore:
    """
    FAISS-backed vector store using SentenceTransformers.
    Each chunk should be a dict with at least: 'text' and 'page' and optionally 'document'.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = None
        self.chunks: List[Dict] = []
        self.embeddings = None
        self.cache = SimpleLRUCache(capacity=256)

    def _normalize(self, vecs: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms

    def create_from_chunks(self, chunks: List[Dict[str, any]]):
        """
        Build FAISS index from chunks list.
        """
        # ensure document name present
        for c in chunks:
            if 'document' not in c:
                c['document'] = c.get('doc', 'Unknown')
        self.chunks = chunks
        texts = [c['text'] for c in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        # normalize for cosine via inner product
        embeddings = embeddings.astype('float32')
        embeddings = self._normalize(embeddings)
        self.embeddings = embeddings
        # use inner-product index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)

    def search(self, query: str, k: int = 3) -> List[Tuple[Dict[str, any], float]]:
        """
        Return top-k (chunk, similarity_score) pairs.
        """
        if self.index is None or len(self.chunks) == 0:
            return []

        # cache key
        key = hashlib.sha256(query.encode('utf-8')).hexdigest()
        cached = self.cache.get((key, k))
        if cached:
            return cached

        q_emb = self.model.encode([query], convert_to_numpy=True).astype('float32')
        q_emb = self._normalize(q_emb)
        # FAISS returns distances = inner product (since normalized -> cosine)
        D, I = self.index.search(q_emb, min(k, len(self.chunks)))
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(dist)))
        self.cache.set((key, k), results)
        return results

    def get_context_for_query(self, query: str, k: int = 3, max_context_length: int = 3000) -> Tuple[str, List[Dict]]:
        """
        Build context string from top-k results and return sources with relevance score.
        """
        results = self.search(query, k=k)
        if not results:
            return "", []

        context_parts = []
        sources = []
        cur_len = 0
        for chunk, score in results:
            txt = chunk['text']
            add_txt = txt
            if cur_len + len(add_txt) > max_context_length:
                remaining = max_context_length - cur_len
                add_txt = add_txt[:max(0, remaining)] + ("..." if remaining > 3 else "")
            context_parts.append(f"[{chunk.get('document','doc')} - Page {chunk.get('page','?')}]\n{add_txt}")
            sources.append({
                "document": chunk.get('document', 'Unknown'),
                "page": chunk.get('page', None),
                "text": chunk.get('text', '')[:800],
                "relevance_score": float(score)
            })
            cur_len += len(add_txt)
            if cur_len >= max_context_length:
                break

        context = "\n\n---\n\n".join(context_parts)
        return context, sources

    # Optional: small helper to clear index
    def clear(self):
        self.index = None
        self.chunks = []
        self.embeddings = None
        self.cache = SimpleLRUCache(capacity=256)
