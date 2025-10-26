from typing import Tuple, List, Dict
from vector_store import VectorStore

class ChatHandler:
    """
    Handles chat interactions with RAG (Retrieval-Augmented Generation).
    """
    
    def __init__(self, model, vector_store: VectorStore):
        """
        Initialize the chat handler.
        
        Args:
            model: Gemini generative model instance
            vector_store: VectorStore instance with indexed documents
        """
        self.model = model
        self.vector_store = vector_store
        self.conversation_history = []
        
    def get_response(self, query: str, k: int = 3) -> Tuple[str, List[Dict]]:
        """
        Get a response to a user query using RAG.
        
        Args:
            query: User's question
            k: Number of relevant chunks to retrieve
            
        Returns:
            Tuple of (response_text, list_of_sources)
        """
       
        context, sources = self.vector_store.get_context_for_query(query, k=k)
        
        if not context:
            return "I couldn't find relevant information in the document to answer your question. Could you rephrase or ask something else?", []
        
        
        prompt = self._build_prompt(query, context)
        
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            self.conversation_history.append({
                'query': query,
                'response': response_text,
                'sources': sources
            })
            
            return response_text, sources
            
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")
    
    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build the prompt for the LLM.
        
        Args:
            query: User's question
            context: Retrieved context from documents
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a helpful study assistant. Your task is to answer questions based ONLY on the provided context from the student's study material.

CONTEXT FROM DOCUMENT:
{context}

STUDENT'S QUESTION:
{query}

INSTRUCTIONS:
1. Answer the question using ONLY information from the provided context above.
2. Be clear, concise, and educational in your response.
3. If the context contains relevant information, provide a comprehensive answer.
4. If you reference specific information, you can mention which page it's from.
5. If the context doesn't contain enough information to answer the question, say so honestly.
6. Do not make up or infer information that's not in the context.
7. Use a friendly, educational tone suitable for a student.

ANSWER:"""
        
        return prompt
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation so far.
        
        Returns:
            Summary string
        """
        if not self.conversation_history:
            return "No conversation yet."
        
        summary_parts = []
        for i, interaction in enumerate(self.conversation_history, 1):
            summary_parts.append(f"{i}. Q: {interaction['query'][:100]}...")
            summary_parts.append(f"   A: {interaction['response'][:100]}...")
        
        return "\n".join(summary_parts)
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
