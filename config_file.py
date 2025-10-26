"""
Configuration settings for Smart Study Buddy
"""

PDF_CONFIG = {
    'chunk_size': 1000,           
    'chunk_overlap': 200,        
    'max_snippet_length': 200,    
}

VECTOR_CONFIG = {
    'embedding_model': 'all-MiniLM-L6-v2',  # Sentence transformer model
    'top_k': 3,                              # Number of chunks to retrieve
    'max_context_length': 3000,              # Max context characters for LLM
}

LLM_CONFIG = {
    'model_name': 'gemini-1.5-flash',       # Gemini model to use
    'temperature': 0.3,                      # Response creativity (0-1)
    'max_output_tokens': 2048,              # Max response length
}

UI_CONFIG = {
    'page_title': 'Smart Study Buddy',
    'page_icon': '📚',
    'layout': 'wide',
    'max_file_size_mb': 10,                 # Max PDF size in MB
    'supported_formats': ['pdf'],
}

MESSAGES = {
    'welcome': " Welcome! Upload a PDF to get started.",
    'processing': "Analyzing your document...",
    'ready': "Ready! Ask me anything about your document.",
    'error_no_text': "Could not extract text from PDF. Please ensure it's a text-based PDF.",
    'error_api_key': "Please set GEMINI_API_KEY in your .env file",
    'error_processing': " Error processing PDF: ",
    'error_query': "Sorry, I encountered an error. Please try again.",
}
