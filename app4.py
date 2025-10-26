# smart_study_buddy_v3.4
"""
Smart Study Buddy v3.4
Changes:
- Structured markdown responses (clear formatting)
- Quiz generation improved (strict JSON parsing, expandable answers)
- Fixed voice input (modern Streamlit query param handling)
- Cleaner chat layout
- Retained gTTS for voice output
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
import io

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

try:
    import soundfile as sf
    from kokoro import KPipeline
    import numpy as np

    HAS_TTS = True
except ImportError:
    st.warning("TTS components not installed")
    HAS_TTS = False

load_dotenv()

st.set_page_config(page_title="Smart Study Buddy v3.4", layout="wide")

st.markdown("""
<style>
body { background-color: #f7f8fb; color: #0f172a; font-family: Inter, sans-serif; }
.source-reference { background: #eef6ff; padding: 0.6rem; border-left: 4px solid #2563eb; border-radius: 0.4rem; margin-top: 0.5rem; }
.metric-card { background: white; padding: 1rem; border-radius: 0.6rem; border: 1px solid #e6eef8; text-align:center; }
.small-muted { color: #64748b; font-size: 0.9rem; }
.voice-button { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 1.2rem; cursor: pointer; }
.voice-status { margin-left: 0.8rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    defaults = {
        'messages': [],
        'vector_store': None,
        'chat_handler': None,
        'documents': {},
        'processing': False,
        'insights': None,
        'voice_enabled': True,
        'query_count': 0,
        'response_times': [],
        'memory_buffer': deque(maxlen=6)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


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


def create_page_thumbnails(pdf_path: str, max_pages=8):
    if not HAS_FITZ:
        return {}
    page_images = {}
    try:
        doc = fitz.open(pdf_path)
        for i in range(min(len(doc), max_pages)):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
            img_bytes = pix.tobytes()
            b64 = base64.b64encode(img_bytes).decode()
            page_images[i+1] = f"data:image/png;base64,{b64}"
        doc.close()
    except Exception:
        return {}
    return page_images


def create_simple_voice_input():
    html = """
    <div style="margin: 0.5rem 0;">
        <button id="voiceButton" class="voice-button">Speak your question</button>
        <span id="voiceStatus" class="voice-status"></span>
    </div>
    <script>
    (function(){
        const btn=document.getElementById('voiceButton');
        const status=document.getElementById('voiceStatus');
        if(!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)){
            status.textContent='Speech recognition not supported';
            btn.disabled=true;
            return;
        }
        const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
        const rec=new SR();
        rec.continuous=false;rec.interimResults=false;rec.lang='en-US';
        btn.onclick=()=>{try{rec.start();}catch(e){}};
        rec.onstart=()=>{btn.textContent='Listening...';btn.style.background='linear-gradient(135deg,#ef4444,#dc2626)';status.textContent='Listening...';};
        rec.onresult=e=>{
            const t=e.results[0][0].transcript;
            status.textContent='Heard: '+t;status.style.color='green';
            const url=new URL(window.location);
            url.searchParams.set('voice_query',t);
            window.location.href=url.href;
        };
        rec.onerror=e=>{status.textContent='Error: '+e.error;status.style.color='red';};
        rec.onend=()=>{btn.textContent='Speak your question';btn.style.background='linear-gradient(135deg,#2563eb,#1d4ed8)';};
    })();
    </script>
    """
    return html


def text_to_speech(text: str) -> str:
    """Generate speech audio from text using Kokoro TTS and return HTML <audio> tag."""

    # Clean text (same as your original)
    safe_text = re.sub(r'\[.*?Page.*?\]', '', text)
    safe_text = safe_text.replace('`', '').replace('*', '').strip()
    if not safe_text:
        return ""

    try:
        # Load Kokoro (cache model to avoid reloading)
        pipeline = KPipeline(lang_code="a")  # 'a' = American English

         # Collect all chunks into one array
        all_audio = []
        for i, (_, _, audio) in enumerate(pipeline(safe_text, voice="af_heart")):
            print(f"Generated chunk {i}")
            all_audio.append(audio)

        # Concatenate into one array
        audio = np.concatenate(all_audio)

        # Write one valid WAV to BytesIO
        buf = io.BytesIO()
        sf.write(buf, audio, samplerate=24000, format="WAV")
        buf.seek(0)

        # Convert to base64 for HTML embedding
        b64 = base64.b64encode(buf.read()).decode("utf-8")

        return f"""
        <audio autoplay controls>
            <source src="data:audio/wav;base64,{b64}" type="audio/wav">
        </audio>
        """

    except Exception as e:
        print("TTS error:", e)
        return ""

def initialize_model():
    key=os.getenv('GEMINI_API_KEY')
    if not key:
        st.error("Missing GEMINI_API_KEY.");st.stop()
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel('gemini-2.5-flash'), 'gemini'
    except Exception as e:
        st.error(f"Model init failed: {e}");st.stop()


def process_pdf_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path=tmp.name
    text, page_map = extract_text_from_pdf(tmp_path)
    if not text.strip():
        os.unlink(tmp_path);return None
    chunks = chunk_text(text, page_map)
    thumbs = create_page_thumbnails(tmp_path)
    os.unlink(tmp_path)
    return {
        'name': uploaded_file.name,
        'text': text,
        'chunks': chunks,
        'insights': generate_insights(text, uploaded_file.name, len(chunks)),
        'page_images': thumbs
    }


def process_documents(uploaded_files):
    if not uploaded_files: return False
    st.session_state.processing=True
    all_chunks=[];st.session_state.documents={}
    prog=st.progress(0,"Processing...")
    for i,f in enumerate(uploaded_files):
        prog.progress((i+1)/len(uploaded_files), f"{f.name}")
        try:
            info=process_pdf_file(f)
            if not info: continue
            for c in info['chunks']: c['document']=info['name']
            all_chunks+=info['chunks']
            st.session_state.documents[info['name']]={'text':info['text'],'chunks':len(info['chunks']),'insights':info['insights'],'page_images':info['page_images']}
        except Exception as e:
            st.error(f"Error {f.name}: {e}")
    prog.empty();st.session_state.processing=False
    if not all_chunks:
        st.error("No text found.");return False
    with st.spinner("Init model..."):
        model,kind=initialize_model()
    vs=VectorStore();vs.create_from_chunks(all_chunks)
    ch=ChatHandler(model,vs)
    st.session_state.vector_store=vs;st.session_state.chat_handler=ch
    st.session_state.messages.append({"role":"assistant","content":"Processed successfully. Ask anything!","sources":[]})
    return True


def add_query_stats(dur,query):
    st.session_state.query_count+=1;st.session_state.response_times.append(dur)


def display_analytics():
    st.markdown("### Session Analytics")
    c1,c2,c3=st.columns(3)
    with c1: st.markdown(f"<div class='metric-card'><h3>{st.session_state.query_count}</h3><div class='small-muted'>Queries</div></div>",unsafe_allow_html=True)
    with c2:
        avg=round(sum(st.session_state.response_times)/len(st.session_state.response_times),2) if st.session_state.response_times else 0
        st.markdown(f"<div class='metric-card'><h3>{avg}s</h3><div class='small-muted'>Avg Time</div></div>",unsafe_allow_html=True)
    with c3:
        texts=" ".join([m['content'] for m in st.session_state.messages if m['role']=='user'])
        top=extract_keywords(texts,top_n=5)
        topics=", ".join([t for t,_ in top]) if top else '—'
        st.markdown(f"<div class='metric-card'><h3 style='font-size:1rem'>{topics}</h3><div class='small-muted'>Top Topics</div></div>",unsafe_allow_html=True)


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




def sidebar_controls():
    with st.sidebar:
        st.header("Controls")
        st.checkbox("Enable voice input",value=st.session_state.voice_enabled,key="voice_enabled")
        st.markdown("---")
        if st.session_state.documents:
            st.markdown("**Loaded Docs:**")
            for n, i in st.session_state.documents.items():
                short_name = n if len(n) <= 40 else n[:37] + "..."
                st.markdown(f"- {short_name} ({i['chunks']} chunks)")
        st.markdown("---")

        if st.session_state.vector_store:
            if st.button("Summarize Docs"): generate_summary_all()
            if st.button("Generate Quiz"): generate_quiz(5)
            if st.button("Clear Chat"):
                st.session_state.messages=[];st.session_state.memory_buffer.clear()
        

        
        


def generate_summary_all():
    if not st.session_state.chat_handler:
        st.error("Model not ready");return
    prompt="Provide a concise summary of the uploaded documents."
    s=time.time()
    r,src=st.session_state.chat_handler.get_response(prompt,k=8)
    d=round(time.time()-s,2);add_query_stats(d,"summary")
    st.session_state.messages.append({"role":"user","content":"Summarize all"})
    st.session_state.messages.append({"role":"assistant","content":r,"sources":src})
    st.rerun()


def main():
    sidebar_controls()
    st.title("Smart Study Buddy v3.4")
    st.markdown("Multi-document AI assistant with structured answers, voice, quizzes, and analytics.")

    if not st.session_state.vector_store:
        st.markdown("### Upload PDFs")
        files=st.file_uploader("Choose PDFs",type=['pdf'],accept_multiple_files=True)
        if files and st.button("Process"):
            process_documents(files);st.rerun()
    else:
        if st.session_state.insights or st.session_state.query_count>0:
            with st.expander("Insights",expanded=False):
                display_analytics()

        left,right=st.columns([3,1])
        with right:
            st.markdown("### Page Previews")
            for n,info in st.session_state.documents.items():
                st.markdown(f"**{n}**")
                for p,uri in info.get('page_images',{}).items():
                    st.image(uri,caption=f"Page {p}",use_column_width=True)

        with left:
            for i,m in enumerate(st.session_state.messages):
                with st.chat_message(m['role']):
                    st.markdown(m['content'])
                    if m['role']=='assistant' and HAS_TTS:
                        if st.button(f"Read Aloud 🔊",key=f"speak_{i}"):
                            st.markdown(text_to_speech(m['content']),unsafe_allow_html=True)

            if st.session_state.voice_enabled:
                st.components.v1.html(create_simple_voice_input(),height=120)

            qp=st.query_params
            voice_query=qp.get('voice_query',[None])[0] if qp else None

            if voice_query:
                st.query_params.clear()
            user_input=voice_query or st.chat_input("Ask a question...")

            if user_input and not st.session_state.processing:
                s=time.time();st.session_state.processing=True
                try:
                    r,src=st.session_state.chat_handler.get_response(user_input,k=4)
                    d=round(time.time()-s,2);add_query_stats(d,user_input)
                    st.session_state.messages.append({"role":"user","content":user_input})
                    st.session_state.messages.append({"role":"assistant","content":r,"sources":src})
                except Exception as e:
                    st.error(f"Error: {e}")
                st.session_state.processing=False;st.rerun()

        st.markdown("---")
        c1,c2,c3=st.columns(3)
        with c1:
            if st.button("Generate Quiz (5)"): generate_quiz(5)
        with c2:
            if st.button("Summarize"): generate_summary_all()
        with c3:
            if st.button("Reset Session"):
                for k in [
                    'messages',
                    'documents',
                    'vector_store',
                    'chat_handler',
                    'insights',
                    'query_count',
                    'response_times',
                ]:
                    st.session_state[k] = [] if k == 'messages' else None
                st.session_state.memory_buffer.clear()
                st.rerun()

    st.markdown("---")
    st.markdown("Built with a RAG pipeline. Model: Gemini.")

if __name__ == "__main__":
    main()

