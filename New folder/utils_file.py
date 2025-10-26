"""
Utility functions for Smart Study Buddy
"""
import os
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()

def get_api_key() -> Optional[str]:
    """
    Get Gemini API key from environment.
    
    Returns:
        API key string or None if not found
    """
    return os.getenv('GEMINI_API_KEY')

def validate_pdf_file(file) -> tuple[bool, str]:
    """
    Validate uploaded PDF file.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if file is None:
        return False, "No file uploaded"
    
    # Check file extension
    if not file.name.lower().endswith('.pdf'):
        return False, "File must be a PDF"
    
    # Check file size (10 MB limit)
    max_size = 10 * 1024 * 1024  
    file.seek(0, 2) 
    size = file.tell()
    file.seek(0) 
    
    if size > max_size:
        return False, f"File too large. Maximum size is 10 MB, yours is {size / 1024 / 1024:.1f} MB"
    
    return True, ""

def get_file_hash(file_content: bytes) -> str:
    """
    Generate hash of file content for caching.
    
    Args:
        file_content: File bytes
        
    Returns:
        SHA256 hash string
    """
    return hashlib.sha256(file_content).hexdigest()

def format_page_reference(page: int) -> str:
    """
    Format page number for display.
    
    Args:
        page: Page number
        
    Returns:
        Formatted string
    """
    return f"Page {page}"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].strip() + suffix

def clean_text(text: str) -> str:
    """
    Clean extracted text from PDF.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
 
    text = ' '.join(text.split())
    
    text = text.replace('\x00', '')
    text = text.replace('\ufffd', '')
    
    return text.strip()

def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    # Rough approximation: ~4 characters per token
    return len(text) // 4

def format_sources_for_display(sources: list) -> str:
    """
    Format source list for HTML display.
    
    Args:
        sources: List of source dictionaries
        
    Returns:
        HTML formatted string
    """
    if not sources:
        return ""
    
    html = "<div class='source-reference'><strong>📚 Sources:</strong><br>"
    
    seen_pages = set()
    for source in sources:
        page = source.get('page', 'Unknown')
        if page not in seen_pages:
            text_preview = truncate_text(source.get('text', ''), 80)
            html += f"• Page {page}: \"{text_preview}\"<br>"
            seen_pages.add(page)
    
    html += "</div>"
    return html

def create_download_link(text: str, filename: str) -> str:
    """
    Create a download link for text content.
    
    Args:
        text: Content to download
        filename: Name of the file
        
    Returns:
        HTML download link
    """
    import base64
    b64 = base64.b64encode(text.encode()).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{filename}">Download</a>'

def get_chat_export(messages: list) -> str:
    """
    Export chat history as text.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Formatted chat text
    """
    export_text = "Smart Study Buddy - Chat History\n"
    export_text += "=" * 50 + "\n\n"
    
    for i, msg in enumerate(messages, 1):
        role = "You" if msg['role'] == 'user' else "AI Assistant"
        export_text += f"[{i}] {role}:\n{msg['content']}\n\n"
        
        if msg.get('sources'):
            export_text += "Sources:\n"
            for source in msg['sources']:
                export_text += f"  - Page {source['page']}\n"
            export_text += "\n"
        
        export_text += "-" * 50 + "\n\n"
    
    return export_text
