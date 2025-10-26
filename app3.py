# smart_study_buddy_v3_1.py
"""
Smart Study Buddy v3.1
Adds:
- Browser-based voice input (SpeechRecognition)
- Browser-based voice output (SpeechSynthesis)
Keeps all v3.0 features: memory, thumbnails, quiz, analytics, fallback models.
"""

import streamlit as st
import google.generativeai as genai
from pathlib import Path
import os
from dotenv import load_dotenv
from collections import Counter, deque
import re
from datetime import datetime
import plotly.graph_objects as go
from pdf_processor import extract_text_from_pdf, chunk_text
from vector_store import VectorStore
from chat_handler import ChatHandler
import base64
import tempfile
import time
import json

# Optional imports for page thumbnails
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

# Optional OpenAI fallback client
try:
    import openai
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

load_dotenv()

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(page_title="Smart Study Buddy v3.1", layout="wide")

# Minimal CSS polish (clean, academic)
st.markdown("""
<style>
    body { background-color: #f7f8fb; color: #0f172a; font-family: Inter, sans-serif; }
    .chat-message { padding: 1rem; border-radius: 0.6rem; margin-bottom: 0.9rem; max-width: 85%; }
    .user-message { background: linear-gradient(90deg,#2563eb,#1d4ed8); color: white; margin-left: auto; }
    .ai-message { background: white; border: 1px solid #e6eef8; color: #0f172a; margin-right: auto; }
    .source-reference { background: #eef6ff; padding: 0.6rem; border-left: 4px solid #2563eb; border-radius: 0.4rem; }
    .metric-card { background: white; padding: 1rem; border-radius: 0.6rem; border: 1px solid #e6eef8; text-align:center; }
    .small-muted { color: #64748b; font-size: 0.9rem; }
    .voice-button { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 1.2rem; cursor: pointer; }
    .voice-status { margin-left: 0.8rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# SESSION STATE INIT
# -------------------------
def init_session_state():
    defaults = {
        'messages': [],                 # chat messages
        'vector_store': None,
        'chat_handler': None,
        'documents': {},                # docname -> {'text','chunks','insights','page_images'}
        'processing': False,
        'insights': None,
        'voice_enabled': True,
        'auto_speak': False,
        'query_count': 0,
        'response_times': [],           # list of durations
        'memory_buffer': deque(maxlen=6)  # store last 3 exchanges (user+assistant pairs => 6 items)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# -------------------------
# Utilities
# -------------------------
def extract_keywords(text: str, top_n: int = 8):
    stop_words = {'the','a','an','and','or','but','in','on','at','to','for','of','with','by','from','is','are','this','that','it','its','they'}
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    filtered = [w for w in words if w not in stop_words]
    return Counter(filtered).most_common(top_n)

def generate_insights(text: str, filename: str, num_chunks: int):
    words = text.split()
    return {
        'filename': filename,
        'total_words': len(words),
        'total_characters': len(text),
        'estimated_reading_time': max(1, len(words) // 200),
        'num_chunks': num_chunks,
        'keywords': extract_keywords(text, top_n=12),
        'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def make_data_uri_from_image_bytes(img_bytes, mime="image/png"):
    b64 = base64.b64encode(img_bytes).decode()
    return f"data:{mime};base64,{b64}"

def create_page_thumbnails(pdf_path: str, max_pages=8):
    """
    Create small thumbnails for first pages. Returns dict page_idx->data_uri.
    Requires PyMuPDF (fitz).
    """
    page_images = {}
    if not HAS_FITZ:
        return page_images
    try:
        doc = fitz.open(pdf_path)
        pages = min(len(doc), max_pages)
        for i in range(pages):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
            img_bytes = pix.tobytes()
            page_images[i+1] = make_data_uri_from_image_bytes(img_bytes)
        doc.close()
    except Exception:
        return {}
    return page_images

# -------------------------
# Voice: Input & Output
# -------------------------
def create_simple_voice_input():
    """Browser voice recognition using Web Speech API (client-side)."""
    voice_input_html = """
    <div style="margin: 0.5rem 0;">
        <button id="voiceButton" class="voice-button">Speak your question</button>
        <span id="voiceStatus" class="voice-status"></span>
    </div>
    <script>
    (function(){
        const btn = document.getElementById('voiceButton');
        const status = document.getElementById('voiceStatus');

        function supported() {
            return ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window);
        }
        if (!supported()) {
            status.textContent = 'Speech recognition not supported in this browser';
            status.style.color = 'red';
            btn.disabled = true;
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        btn.addEventListener('click', function(){
            try {
                recognition.start();
            } catch(e) {
                // some browsers may throw if already started
            }
        });

        recognition.onstart = () => {
            btn.textContent = 'Listening... (click again to stop)';
            btn.style.background = 'linear-gradient(135deg,#ef4444,#dc2626)';
            status.textContent = 'Listening...';
            status.style.color = '#1f2937';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            status.textContent = 'Heard: ' + transcript;
            status.style.color = 'green';
            // send transcript back to Streamlit via URL param
            const url = new URL(window.location);
            url.searchParams.set('voice_query', transcript);
            window.location.href = url.href;
        };

        recognition.onerror = (event) => {
            status.textContent = 'Error: ' + event.error;
            status.style.color = 'red';
        };

        recognition.onend = () => {
            btn.textContent = 'Speak your question';
            btn.style.background = 'linear-gradient(135deg,#2563eb,#1d4ed8)';
        };
    })();
    </script>
    """
    return voice_input_html

def text_to_speech(text: str) -> str:
    """Convert assistant text to speech using browser TTS (client-side)."""
    safe_text = text.replace('`', '').replace('*', '').replace('\\', '')
    js = f"""
    <script>
    (function() {{
        try {{
            const utter = new SpeechSynthesisUtterance(`{safe_text}`);
            utter.rate = 0.95;
            utter.pitch = 1.0;
            speechSynthesis.cancel();
            speechSynthesis.speak(utter);
        }} catch (e) {{
            console.error('TTS error', e);
        }}
    }})();
    </script>
    """
    return js

# -------------------------
# Model initialization with fallback
# -------------------------
class OpenAIFallbackModel:
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        if not HAS_OPENAI:
            raise RuntimeError("openai package not installed for fallback.")
        openai.api_key = api_key
        self.model_name = model_name

    def generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2):
        try:
            resp = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[{"role":"user","content":prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = resp['choices'][0]['message']['content']
            return content
        except Exception:
            resp = openai.Completion.create(model=self.model_name, prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            return resp['choices'][0]['text']

def initialize_model_with_fallback():
    gem_key = os.getenv('GEMINI_API_KEY')
    if gem_key:
        try:
            genai.configure(api_key=gem_key)
            return genai.GenerativeModel('gemini-2.5-flash'), 'gemini'
        except Exception:
            st.warning("Gemini init failed, attempting OpenAI fallback.")

    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key and HAS_OPENAI:
        try:
            fallback = OpenAIFallbackModel(openai_key, model_name=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'))
            return fallback, 'openai'
        except Exception as e:
            st.error(f"OpenAI fallback failed: {str(e)}")
            st.stop()
    else:
        st.error("No GEMINI_API_KEY set and OpenAI fallback not available. Set GEMINI_API_KEY or OPENAI_API_KEY.")
        st.stop()

# -------------------------
# Processing PDFs / multi-doc support
# -------------------------
def process_pdf_file(uploaded_file):
    temp_path = Path(f"temp_{uploaded_file.name}")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    pdf_text, page_mapping = extract_text_from_pdf(str(temp_path))
    if not pdf_text.strip():
        temp_path.unlink()
        return None
    chunks = chunk_text(pdf_text, page_mapping)
    page_images = create_page_thumbnails(str(temp_path), max_pages=12)
    temp_path.unlink()
    return {
        'name': uploaded_file.name,
        'text': pdf_text,
        'chunks': chunks,
        'insights': generate_insights(pdf_text, uploaded_file.name, len(chunks)),
        'page_images': page_images
    }

def process_documents(uploaded_files):
    if not uploaded_files:
        return False
    st.session_state.processing = True
    all_chunks = []
    st.session_state.documents = {}
    progress = st.progress(0)
    for idx, f in enumerate(uploaded_files):
        st.info(f"Processing {f.name} ({idx+1}/{len(uploaded_files)})")
        try:
            docinfo = process_pdf_file(f)
            if not docinfo:
                st.warning(f"Could not extract text from {f.name}")
                continue
            for c in docinfo['chunks']:
                c['document'] = docinfo['name']
            all_chunks.extend(docinfo['chunks'])
            st.session_state.documents[docinfo['name']] = {
                'text': docinfo['text'],
                'chunks': len(docinfo['chunks']),
                'insights': docinfo['insights'],
                'page_images': docinfo['page_images']
            }
        except Exception as e:
            st.error(f"Error processing {f.name}: {str(e)}")
        progress.progress((idx+1)/len(uploaded_files))
    progress.empty()
    st.session_state.processing = False

    if not all_chunks:
        st.error("No text could be extracted from uploaded documents.")
        return False

    model_obj, model_kind = initialize_model_with_fallback()
    vector_store = VectorStore()
    vector_store.create_from_chunks(all_chunks)
    chat_handler = ChatHandler(model_obj, vector_store)
    st.session_state.vector_store = vector_store
    st.session_state.chat_handler = chat_handler
    if len(st.session_state.documents) == 1:
        st.session_state.insights = next(iter(st.session_state.documents.values()))['insights']
    st.session_state.messages.append({"role":"assistant","content":f"Processed {len(st.session_state.documents)} document(s). Ask anything.", "sources":[]})
    return True

# -------------------------
# Chat memory helper
# -------------------------
def build_memory_context():
    if not st.session_state.memory_buffer:
        return ""
    items = list(st.session_state.memory_buffer)
    text = "Previous conversation snippets:\n"
    for i, item in enumerate(items):
        role = "User" if i % 2 == 0 else "Assistant"
        text += f"{role}: {item}\n"
    text += "\nNow answer the next user question based on the document context and above conversation.\n"
    return text

# -------------------------
# Analytics helpers
# -------------------------
def add_query_stats(duration, user_text):
    st.session_state.query_count += 1
    st.session_state.response_times.append(duration)

def display_analytics():
    st.markdown("### Session Analytics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><h3>{st.session_state.query_count}</h3><div class='small-muted'>Queries</div></div>", unsafe_allow_html=True)
    with col2:
        avg = round(sum(st.session_state.response_times)/len(st.session_state.response_times), 2) if st.session_state.response_times else 0
        st.markdown(f"<div class='metric-card'><h3>{avg}s</h3><div class='small-muted'>Avg Response Time</div></div>", unsafe_allow_html=True)
    with col3:
        user_texts = " ".join([m["content"] for m in st.session_state.messages if m["role"]=="user"])
        top = extract_keywords(user_texts, top_n=6)
        topics = ", ".join([t for t,_ in top]) if top else "—"
        st.markdown(f"<div class='metric-card'><h3 style='font-size:1rem'>{topics}</h3><div class='small-muted'>Top Topics</div></div>", unsafe_allow_html=True)

    if st.session_state.response_times:
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=st.session_state.response_times, nbinsx=10))
        fig.update_layout(title="Response time distribution (s)", xaxis_title="Seconds", yaxis_title="Count", height=300)
        st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Quiz Mode
# -------------------------
def generate_quiz(num_questions=5):
    if not st.session_state.chat_handler:
        st.error("No model available.")
        return

    prompt = f"Generate {num_questions} multiple-choice questions (each with 4 options and highlight the correct answer) based on the uploaded documents. Provide them in JSON with keys q1..q{num_questions} as: {{'question':str,'options':[...],'answer':index}}"
    start = time.time()
    response, sources = st.session_state.chat_handler.get_response(prompt, k=5)
    duration = round(time.time()-start, 2)
    add_query_stats(duration, "generate_quiz")
    quiz = []
    try:
        json_text = response[response.find('{'):response.rfind('}')+1]
        data = json.loads(json_text)
        for k, v in data.items():
            quiz.append(v)
    except Exception:
        st.warning("Could not parse quiz JSON; showing raw output.")
        st.write(response)
        return

    for i, q in enumerate(quiz, start=1):
        st.markdown(f"**Q{i}. {q.get('question','')}**")
        opts = q.get('options', [])
        for idx, opt in enumerate(opts):
            st.write(f"{chr(65+idx)}. {opt}")
        with st.expander("Show Answer"):
            answer_idx = q.get('answer', 0)
            st.markdown(f"**Answer: {chr(65+answer_idx)}**")

# -------------------------
# UI: Sidebar
# -------------------------
def sidebar_controls():
    with st.sidebar:
        st.header("Controls")
        st.checkbox("Enable voice input", value=st.session_state.voice_enabled, key="voice_enabled")
        st.checkbox("Auto-speak answers", value=st.session_state.auto_speak, key="auto_speak")
        st.markdown("---")
        if st.session_state.documents:
            st.markdown("**Loaded Documents**")
            for name, info in st.session_state.documents.items():
                st.markdown(f"- {name} ({info['chunks']} chunks)")
            st.markdown("---")
        if st.session_state.vector_store:
            if st.button("Summarize Documents"):
                generate_summary_all()
            if st.button("Generate Quiz"):
                generate_quiz(5)
            if st.button("Clear chat"):
                st.session_state.messages = []
        st.markdown("---")
        st.markdown("### About")
        st.markdown("Smart Study Buddy v3.1 — built for hackathon. Multi-document RAG, voice, quizzes, analytics.")
        st.markdown("Model: Gemini primary, OpenAI fallback if configured.")
        st.markdown("Built by: Your Team")
        st.markdown("Source code: Add your repo link here")

# -------------------------
# Summarization helper
# -------------------------
def generate_summary_all():
    if not st.session_state.chat_handler:
        st.error("Model not ready")
        return
    prompt = "Provide a concise summary of the main topics across the uploaded documents."
    start = time.time()
    response, sources = st.session_state.chat_handler.get_response(prompt, k=5)
    duration = round(time.time()-start, 2)
    add_query_stats(duration, "generate_summary_all")
    st.session_state.messages.append({"role":"user","content":"Generate summary"})
    st.session_state.messages.append({"role":"assistant","content":response, "sources":sources})

# -------------------------
# MAIN
# -------------------------
def main():
    sidebar_controls()
    st.title("Smart Study Buddy v3.1")
    st.markdown("Multi-document AI assistant with memory, page previews, quizzes, analytics, and voice.")

    # Upload area
    if not st.session_state.vector_store:
        st.markdown("### Upload PDFs")
        uploaded_files = st.file_uploader("Choose PDF files", type=['pdf'], accept_multiple_files=True)
        if uploaded_files:
            if st.button("Process documents"):
                process_documents(uploaded_files)
                st.experimental_rerun()
    else:
        # insights expander
        if st.session_state.insights:
            with st.expander("Document Insights", expanded=False):
                display_analytics()
                if len(st.session_state.documents) == 1:
                    docname = next(iter(st.session_state.documents))
                    ins = st.session_state.documents[docname]['insights']
                    st.markdown(f"**{docname}** — {ins['total_words']:,} words, {ins['estimated_reading_time']} min read")
                    kw = ", ".join([k for k,_ in ins['keywords']])
                    st.markdown(f"**Keywords:** {kw}")

        st.markdown("---")
        left, right = st.columns([3,1])
        with right:
            st.markdown("### Page Previews")
            for name, info in st.session_state.documents.items():
                st.markdown(f"**{name}**")
                page_images = info.get('page_images', {})
                if page_images:
                    cols = st.columns(2)
                    i = 0
                    for p, uri in page_images.items():
                        cols[i%2].image(uri, caption=f"Page {p}", use_column_width=True)
                        i += 1
                else:
                    st.write("No thumbnails (install PyMuPDF to enable).")

        with left:
            # show chat
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"<div class='chat-message user-message'><strong>User</strong><div>{message['content']}</div></div>", unsafe_allow_html=True)
                else:
                    content = message['content']
                    if len(content) > 650:
                        with st.expander("View full answer"):
                            st.markdown(f"<div class='chat-message ai-message'><strong>Assistant</strong><div>{content}</div></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='chat-message ai-message'><strong>Assistant</strong><div>{content}</div></div>", unsafe_allow_html=True)

                    # Auto-speak assistant response if enabled (only for the most recent message)
                    if st.session_state.auto_speak and message == st.session_state.messages[-1]:
                        st.markdown(text_to_speech(message["content"]), unsafe_allow_html=True)

                    if message.get("sources"):
                        sources_by_doc = {}
                        for s in message["sources"]:
                            doc = s.get('document','Unknown')
                            sources_by_doc.setdefault(doc, []).append(s)
                        src_html = "<div class='source-reference'><strong>Sources</strong><br>"
                        for doc, list_s in sources_by_doc.items():
                            src_html += f"<strong>{doc}</strong><br>"
                            for s in list_s:
                                txt = s.get('text','')[:100]
                                src_html += f"• Page {s.get('page','?')}: \"{txt}...\"<br>"
                        src_html += "</div>"
                        st.markdown(src_html, unsafe_allow_html=True)

            # voice input: check for voice query param
            query_params = st.experimental_get_query_params()
            voice_query = query_params.get("voice_query", [None])[0] if query_params else None

            if st.session_state.voice_enabled:
                # render voice button component
                st.components.v1.html(create_simple_voice_input(), height=120)

            # Get user input (voice or typed)
            user_input = voice_query if voice_query else st.chat_input("Ask a question...")

            # Clear voice_query param once used
            if voice_query:
                try:
                    st.experimental_set_query_params()
                except Exception:
                    # best-effort: if clearing fails, ignore
                    pass

            if user_input and not st.session_state.processing:
                memory_ctx = build_memory_context()
                final_prompt = memory_ctx + "\nUser: " + user_input
                start = time.time()
                st.session_state.processing = True
                try:
                    response, sources = st.session_state.chat_handler.get_response(final_prompt, k=4)
                    duration = round(time.time() - start, 2)
                    add_query_stats(duration, user_input)
                    st.session_state.memory_buffer.append(user_input)
                    st.session_state.memory_buffer.append(response if isinstance(response, str) else str(response))
                    st.session_state.messages.append({"role":"user","content":user_input})
                    st.session_state.messages.append({"role":"assistant","content":response, "sources": sources})
                except Exception as e:
                    st.session_state.messages.append({"role":"assistant","content":f"Error: {str(e)}", "sources":[]})
                finally:
                    st.session_state.processing = False
                st.experimental_rerun()

        st.markdown("---")
        cols = st.columns(3)
        with cols[0]:
            if st.button("Generate Quiz (5)"):
                generate_quiz(5)
        with cols[1]:
            if st.button("Summarize"):
                generate_summary_all()
        with cols[2]:
            if st.button("Reset Session"):
                st.session_state.messages = []
                st.session_state.documents = {}
                st.session_state.vector_store = None
                st.session_state.chat_handler = None
                st.session_state.insights = None
                st.session_state.query_count = 0
                st.session_state.response_times = []
                st.session_state.memory_buffer.clear()
                st.experimental_rerun()

    st.markdown("---")
    st.markdown("Built with a RAG pipeline. Primary model: Gemini (if configured). Fallback: OpenAI (if configured).")

if __name__ == "__main__":
    main()
