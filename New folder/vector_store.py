import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import faiss

class VectorStore:
    """
    Simple vector store using FAISS for efficient similarity search.
    Uses sentence transformers for embeddings.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the vector store.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = None
        self.chunks = []
        
    def create_from_chunks(self, chunks: List[Dict[str, any]]):
        """
        Create vector index from text chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and metadata
        """
        self.chunks = chunks
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)
        
    def search(self, query: str, k: int = 3) -> List[Tuple[Dict[str, any], float]]:
        """
        Search for most similar chunks to the query.
        
        Args:
            query: The search query
            k: Number of results to return
            
        Returns:
            List of (chunk, distance) tuples
        """
        if self.index is None or len(self.chunks) == 0:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search
        distances, indices = self.index.search(query_embedding, min(k, len(self.chunks)))
        
        # Return results with metadata
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(distance)))
        
        return results
    
    def get_context_for_query(self, query: str, k: int = 3, max_context_length: int = 3000) -> Tuple[str, List[Dict]]:
        """
        Get context string and sources for a query.
        
        Args:
            query: The search query
            k: Number of chunks to retrieve
            max_context_length: Maximum length of context in characters
            
        Returns:
            Tuple of (context_string, list_of_source_dicts)
        """
        results = self.search(query, k)
        
        if not results:
            return "", []
        
        context_parts = []
        sources = []
        current_length = 0
        
        for chunk, distance in results:
            chunk_text = chunk['text']
            
            if current_length + len(chunk_text) > max_context_length:
                # Truncate to fit
                remaining = max_context_length - current_length
                chunk_text = chunk_text[:remaining] + "..."
            
            context_parts.append(f"[Page {chunk['page']}]\n{chunk_text}")
            sources.append({
                'page': chunk['page'],
                'text': chunk['text'],
                'relevance_score': 1.0 / (1.0 + distance)  # Convert distance to similarity
            })
            
            current_length += len(chunk_text)
            
            if current_length >= max_context_length:
                break
        
        context = "\n\n---\n\n".join(context_parts)
        return context, sources
