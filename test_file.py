"""
Unit tests for Smart Study Buddy components
"""
import unittest
import numpy as np
from pdf_processor import chunk_text, extract_relevant_snippet
from vector_store import VectorStore

class TestPdfProcessor(unittest.TestCase):
    
    def test_chunk_text(self):
        """Test text chunking"""
        text = "This is a test. " * 100  # Create long text
        page_mapping = {i: 1 for i in range(len(text))}
        
        chunks = chunk_text(text, page_mapping, chunk_size=100, overlap=20)
        
        self.assertGreater(len(chunks), 0)
        self.assertTrue(all('text' in chunk for chunk in chunks))
        self.assertTrue(all('page' in chunk for chunk in chunks))
    
    def test_extract_relevant_snippet(self):
        """Test snippet extraction"""
        text = "This is a very long sentence that should be truncated. " * 10
        snippet = extract_relevant_snippet(text, max_length=100)
        
        self.assertLessEqual(len(snippet), 110)  # Allow for ellipsis
        self.assertIn("This is a very long", snippet)
    
    def test_empty_text(self):
        """Test handling of empty text"""
        page_mapping = {}
        chunks = chunk_text("", page_mapping)
        
        self.assertEqual(len(chunks), 0)

class TestVectorStore(unittest.TestCase):
    
    def setUp(self):
        """Set up test vector store"""
        self.vector_store = VectorStore()
        
        # Create sample chunks
        self.sample_chunks = [
            {'text': 'Machine learning is a subset of artificial intelligence.', 'page': 1},
            {'text': 'Deep learning uses neural networks with multiple layers.', 'page': 2},
            {'text': 'Python is a popular programming language for data science.', 'page': 3},
        ]
    
    def test_create_from_chunks(self):
        """Test vector store creation"""
        self.vector_store.create_from_chunks(self.sample_chunks)
        
        self.assertIsNotNone(self.vector_store.index)
        self.assertEqual(len(self.vector_store.chunks), 3)
    
    def test_search(self):
        """Test similarity search"""
        self.vector_store.create_from_chunks(self.sample_chunks)
        
        results = self.vector_store.search("What is machine learning?", k=2)
        
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 2)
        
        # First result should be about machine learning
        self.assertIn('machine learning', results[0][0]['text'].lower())
    
    def test_get_context_for_query(self):
        """Test context retrieval"""
        self.vector_store.create_from_chunks(self.sample_chunks)
        
        context, sources = self.vector_store.get_context_for_query("neural networks", k=2)
        
        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)
        self.assertIsInstance(sources, list)
        self.assertGreater(len(sources), 0)
    
    def test_empty_search(self):
        """Test search on empty store"""
        results = self.vector_store.search("test query", k=3)
        self.assertEqual(len(results), 0)

class TestUtils(unittest.TestCase):
    
    def test_truncate_text(self):
        """Test text truncation"""
        from utils import truncate_text
        
        long_text = "This is a very long text " * 10
        truncated = truncate_text(long_text, max_length=50)
        
        self.assertLessEqual(len(truncated), 53)  # 50 + "..."
        self.assertTrue(truncated.endswith("..."))
    
    def test_clean_text(self):
        """Test text cleaning"""
        from utils import clean_text
        
        dirty_text = "Text   with\n\n\nmultiple\t\tspaces"
        cleaned = clean_text(dirty_text)
        
        self.assertEqual(cleaned, "Text with multiple spaces")
    
    def test_estimate_tokens(self):
        """Test token estimation"""
        from utils import estimate_tokens
        
        text = "This is a test sentence."
        tokens = estimate_tokens(text)
        
        self.assertGreater(tokens, 0)
        self.assertIsInstance(tokens, int)

def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)

if __name__ == '__main__':
    run_tests()
