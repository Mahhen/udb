import streamlit as st
import google.generativeai as genai
from pathlib import Path
import os
from pdf_processor import extract_text_from_pdf, chunk_text
from vector_store import VectorStore
from chat_handler import ChatHandler
from dotenv import load_dotenv

# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------
st.set_page_config(
    page_title="Smart Study Buddy",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# GLOBAL STYLES (dark mode inspired academic theme)
# ------------------------------------------------------------
st.markdown("""
<style>
    html, body, [class*="stAppViewContainer"], [class*="stApp"] {
        background-color: #0d1117 !important;
        color: #e6edf3;
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4 {
        color: #ffffff;
        font-weight: 600;
    }

    p, li, div, span {
        color: #e6edf3;
    }

    .stTextInput > div > div > input {
        border-radius: 0.6rem;
        background-color: #161b22;
        color: #ffffff;
        border: 1px solid #30363d;
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 0.5rem;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1e40af, #1d4ed8);
        transform: scale(1.02);
    }

    .stFileUploader {
        background-color: #161b22;
        border: 2px dashed #30363d;
        border-radius: 1rem;
        padding: 2.5rem;
        transition: all 0.3s ease;
    }
    .stFileUploader:hover {
        border-color: #2563eb;
        background-color: #1a1f27;
    }

    .chat-message {
        border-radius: 0.75rem;
        padding: 1rem 1.25rem;
        margin-bottom: 1.2rem;
        max-width: 85%;
        line-height: 1.6;
    }

    .user-message {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white;
        margin-left: auto;
        border: none;
        box-shadow: 0 3px 12px rgba(37,99,235,0.3);
    }

    .ai-message {
        background-color: #161b22;
        border: 1px solid #30363d;
        margin-right: auto;
        box-shadow: 0 3px 12px rgba(0,0,0,0.2);
    }

    .source-reference {
        background-color: #1e293b;
        border-left: 4px solid #2563eb;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
        border-radius: 0.5rem;
        color: #cbd5e1;
    }

    hr {
        border: 1px solid #30363d;
        margin: 2rem 0;
    }

    /* Input bar */
    .stChatInputContainer {
        background-color: #0d1117 !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# SESSION STATE INIT
# ------------------------------------------------------------
for key in ["messages", "vector_store", "chat_handler", "document_name", "processing"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "messages" else None if key != "processing" else False


# ------------------------------------------------------------
# GEMINI INITIALIZATION
# ------------------------------------------------------------
def initialize_gemini():
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("Please set GEMINI_API_KEY in your .env file")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')


# ------------------------------------------------------------
# PDF PROCESSING
# ------------------------------------------------------------
def process_pdf(uploaded_file):
    try:
        with st.spinner(f"Analyzing {uploaded_file.name}..."):
            temp_path = Path(f"temp_{uploaded_file.name}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            pdf_text, page_mapping = extract_text_from_pdf(str(temp_path))
            if not pdf_text.strip():
                st.error("Could not extract text from PDF. Please ensure it's a text-based PDF.")
                temp_path.unlink()
                return False

            chunks = chunk_text(pdf_text, page_mapping)
            model = initialize_gemini()
            vector_store = VectorStore()
            vector_store.create_from_chunks(chunks)
            chat_handler = ChatHandler(model, vector_store)

            st.session_state.vector_store = vector_store
            st.session_state.chat_handler = chat_handler
            st.session_state.document_name = uploaded_file.name
            temp_path.unlink()

            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Finished analyzing **{uploaded_file.name}**. You can now ask questions based on its content.",
                "sources": []
            })
            return True
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        if temp_path.exists():
            temp_path.unlink()
        return False


# ------------------------------------------------------------
# RESET
# ------------------------------------------------------------
def reset_conversation():
    for key in ["messages", "vector_store", "chat_handler", "document_name"]:
        st.session_state[key] = None if key != "messages" else []
    st.session_state.processing = False


# ------------------------------------------------------------
# MAIN APP
# ------------------------------------------------------------
def main():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Smart Study Buddy")
        st.markdown("<p style='color:#9ca3af;'>Upload your academic material and query it intelligently using AI-powered retrieval.</p>", unsafe_allow_html=True)
    with col2:
        if st.session_state.document_name:
            st.markdown(f"**Current Document:**<br><span style='color:#93c5fd;'>{st.session_state.document_name}</span>", unsafe_allow_html=True)
            if st.button("Upload New Document", use_container_width=True):
                reset_conversation()
                st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # -------------------------------------------
    # FILE UPLOAD SECTION
    # -------------------------------------------
    if not st.session_state.vector_store:
        st.markdown("### Upload Your Study Material")
        st.markdown("<p style='color:#9ca3af;'>Start by uploading a PDF textbook, research paper, or lecture notes.</p>", unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            label_visibility="collapsed",
            help="Only text-based PDFs are supported."
        )

        if uploaded_file:
            st.success(f"File loaded: {uploaded_file.name}")
            if st.button("Process Document", use_container_width=True, type="primary"):
                success = process_pdf(uploaded_file)
                if success:
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("""
        <div style='display:flex; justify-content:space-between;'>
            <div style='flex:1; margin-right:1rem; background-color:#161b22; border:1px solid #30363d; border-radius:0.75rem; padding:1.5rem;'>
                <h3 style='color:#60a5fa;'>Smart Answers</h3>
                <p style='color:#9ca3af;'>Receive context-aware explanations drawn directly from your uploaded PDFs.</p>
            </div>
            <div style='flex:1; margin:0 1rem; background-color:#161b22; border:1px solid #30363d; border-radius:0.75rem; padding:1.5rem;'>
                <h3 style='color:#60a5fa;'>Source References</h3>
                <p style='color:#9ca3af;'>Each response includes the exact page and section for verification.</p>
            </div>
            <div style='flex:1; margin-left:1rem; background-color:#161b22; border:1px solid #30363d; border-radius:0.75rem; padding:1.5rem;'>
                <h3 style='color:#60a5fa;'>Natural Chat</h3>
                <p style='color:#9ca3af;'>Ask questions naturally, and get scholarly answers in conversational form.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------
    # CHAT INTERFACE
    # -------------------------------------------
    else:
        st.markdown("""
        <div style='background:linear-gradient(90deg,#2563eb,#4f46e5);padding:1rem 1.5rem;border-radius:0.5rem;margin-bottom:1.5rem;'>
            <h3 style='color:white;margin:0;'>Chat with Your Document</h3>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <div style='font-weight:500;margin-bottom:0.4rem;'>You</div>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message ai-message">
                        <div style='font-weight:500;margin-bottom:0.4rem;color:#93c5fd;'>AI Assistant</div>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                    if message.get("sources"):
                        src_html = "<div class='source-reference'><strong>References:</strong><br>"
                        for src in message["sources"]:
                            src_html += f"• Page {src['page']}: “{src['text'][:100]}...”<br>"
                        src_html += "</div>"
                        st.markdown(src_html, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        user_input = st.chat_input("Ask a question about your document...")
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        if user_input and not st.session_state.processing:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.processing = True
            try:
                with st.spinner("Analyzing..."):
                    response, sources = st.session_state.chat_handler.get_response(user_input)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"An error occurred: {str(e)}",
                    "sources": []
                })
            finally:
                st.session_state.processing = False
            st.rerun()


if __name__ == "__main__":
    main()
