try:
    # Prefer the commonly available 'fitz' module and alias it to 'pymupdf'
    import fitz as pymupdf
except Exception:
    # Fall back to 'pymupdf' name if available, otherwise raise a clear error.
    try:
        import pymupdf
    except Exception as e:
        raise ImportError("PyMuPDF is required: install with 'pip install pymupdf'") from e

from typing import List, Dict, Tuple

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, Dict[int, int]]:
    """
    Extract text from PDF and maintain page mapping.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Tuple of (full_text, page_mapping) where page_mapping maps 
        character positions to page numbers
    """
    doc = pymupdf.open(pdf_path)
    full_text = ""
    page_mapping = {}
    current_position = 0
    
    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text()
        
        # Store the page number for this text range
        for i in range(len(page_text)):
            page_mapping[current_position + i] = page_num
        
        full_text += page_text
        current_position += len(page_text)
    
    doc.close()
    return full_text, page_mapping

def chunk_text(text: str, page_mapping: Dict[int, int], 
               chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, any]]:
    """
    Split text into chunks with overlap while preserving page information.
    
    Args:
        text: The full text to chunk
        page_mapping: Dictionary mapping character positions to page numbers
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of dictionaries containing chunk text and metadata
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundaries
        if end < len(text):
            # Look for sentence endings within the last 100 chars
            sentence_ends = ['.', '!', '?', '\n']
            best_break = end
            
            for i in range(end - 100, end):
                if i > 0 and text[i] in sentence_ends and text[i + 1].isspace():
                    best_break = i + 1
                    break
            
            end = best_break
        else:
            end = len(text)
        
        chunk_text = text[start:end].strip()
        
        if chunk_text:
            # Determine the page number for this chunk (use the middle position)
            mid_position = start + (end - start) // 2
            page_num = page_mapping.get(mid_position, 1)
            
            chunks.append({
                'text': chunk_text,
                'page': page_num,
                'start_pos': start,
                'end_pos': end
            })
        
        # Move start position with overlap
        start = end - overlap if end < len(text) else len(text)
    
    return chunks

def extract_relevant_snippet(text: str, max_length: int = 200) -> str:
    """
    Extract a relevant snippet from text, preferring complete sentences.
    
    Args:
        text: The text to extract from
        max_length: Maximum length of the snippet
        
    Returns:
        Extracted snippet
    """
    if len(text) <= max_length:
        return text
    
    # Try to find a good breaking point
    snippet = text[:max_length]
    
    # Look for the last sentence boundary
    for punct in ['. ', '! ', '? ', '\n']:
        idx = snippet.rfind(punct)
        if idx > max_length * 0.5:  # Only break if we're past halfway
            return snippet[:idx + 1].strip()
    
    # If no good break found, just truncate with ellipsis
    return snippet.strip() + "..."
