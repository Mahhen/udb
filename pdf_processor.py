# pdf_processor.py
try:
    import fitz as pymupdf
except Exception:
    try:
        import pymupdf
    except Exception as e:
        raise ImportError("PyMuPDF is required: pip install pymupdf") from e

from typing import List, Dict, Tuple
import re

# optional OCR components
try:
    from pdf2image import convert_from_path
    import pytesseract
    HAS_OCR = True
except Exception:
    HAS_OCR = False

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, Dict[int, int]]:
    """
    Extract text from PDF and create a page mapping.
    Returns: (full_text, page_mapping) where page_mapping maps char index -> page number
    """
    doc = pymupdf.open(pdf_path)
    full_text = ""
    page_mapping: Dict[int, int] = {}
    current_pos = 0

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text().strip() or ""
        # If page_text is empty and OCR is available, try OCR
        if not page_text and HAS_OCR:
            try:
                pil_images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=200)
                if pil_images:
                    page_text = pytesseract.image_to_string(pil_images[0])
            except Exception:
                page_text = ""
        # map characters to page number
        for i in range(len(page_text)):
            page_mapping[current_pos + i] = page_num
        full_text += page_text + "\n\n"
        current_pos += len(page_text) + 2  # account for added separators

    doc.close()
    return full_text, page_mapping

def chunk_text(text: str, page_mapping: Dict[int, int],
               chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, any]]:
    """
    Split the full text into overlapping chunks and preserve page metadata.
    Returns list of dicts: { 'text', 'page', 'start_pos', 'end_pos', 'tokens' }
    """
    chunks = []
    start = 0
    n = len(text)

    sentence_boundaries = re.compile(r'([.!?]\s+)')

    while start < n:
        end = start + chunk_size
        if end < n:
            # attempt to break on sentence boundary near 'end'
            search_start = max(start, end - 120)
            snippet = text[search_start:end + 1]
            m = list(sentence_boundaries.finditer(snippet))
            if m:
                last = m[-1]
                # compute new end (relative to entire text)
                new_end = search_start + last.end()
                if new_end - start > int(chunk_size * 0.4):
                    end = new_end
        else:
            end = n

        chunk_txt = text[start:end].strip()
        if chunk_txt:
            mid = start + (end - start) // 2
            page_num = page_mapping.get(mid, 1)
            tokens = len(chunk_txt.split())
            chunks.append({
                "text": chunk_txt,
                "page": page_num,
                "start_pos": start,
                "end_pos": end,
                "tokens": tokens
            })

        # move start forward with overlap
        if end >= n:
            break
        start = end - overlap

    return chunks

def extract_relevant_snippet(text: str, max_length: int = 200) -> str:
    """
    Return a short snippet favoring full sentences.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    # try to end at punctuation
    for punct in ['. ', '? ', '! ', '\n']:
        idx = text.rfind(punct, 0, max_length)
        if idx and idx > max_length * 0.5:
            return text[:idx+1].strip()
    return text[:max_length].strip() + "..."
