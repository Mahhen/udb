"""
Enhanced version of Smart Study Buddy with additional features:
- Chat history export
- Document summary
- Multiple retrieval modes
- Better error handling
- Performance metrics
"""

import streamlit as st
import google.generativeai as genai
from pathlib import Path
import os
import time
from pdf_processor import extract_text_from_pdf, chunk_text
from vector_store import VectorStore
from chat_handler import ChatHandler
from utils import (
    load_environment, get_api_key, validate_pdf_file,
    get_chat_export, format_sources_for_display
)
from config import PDF_CONFIG, VECTOR_CONFIG, LLM_CONFIG, UI_CONFIG, MESSAGES

# Load environment
load_environment()

# Page configuration
st.set_page_config(
    page_title=UI_CONFIG['page_title'],
    page_icon=UI_CONFIG['page_icon'],
    layout=UI_CONFIG['layout'],
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTextInput > div > div > input { border-radius: 20px; }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #3b82f6;
        color: white;
        align-self: flex-end;
        margin-left: 20%;
    }
    .ai-message {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        align-self: flex-start;
        margin-right: 20%;
    }
    .source-reference {
        background-color: #f3f4f6;
        padding: 0.5rem;
        border-left: 3px solid #3b82f6;
        margin-top: 0.5rem;
        font-size: 0.85rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    defaults = {
        'messages': [],
        'vector_store': None,
        'chat_handler': None,
        'document_name': None,
        'processing': False,
        'document_stats': None,
        'retrieval_mode': 'balanced',
        'show_sources': True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

def initialize_gemini():
    """Initialize Gemini API with error handling"""
    api_key = get_api_key()
    if not api_key:
        st.error(MESSAGES['error_api_key'])
        st.info("Get your API key from: https://makersuite.google.com/app/apikey")
        st.stop()
    
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(LLM_CONFIG['model_name'])
    except Exception as e:
        st.error(f"Failed to initialize Gemini: {str(e)}")
        st.stop()

def process_pdf(uploaded_file):
    """Process uploaded PDF with metrics"""
    start_time = time.time()
    
    # Validate file
    is_valid, error_msg = validate_pdf_file(uploaded_file)
    if not is_valid:
        st.error(error_msg)
        return False
    
    try:
        with st.spinner(f"📖 Analyzing {uploaded_file.name}..."):
            # Save uploaded file temporarily
            temp_path = Path(f"temp_{uploaded_file.name}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Extract text from PDF
            pdf_text, page_mapping = extract_text_from_pdf(str(temp_path))
            
            if not pdf_text.strip():
                st.error(MESSAGES['error_no_text'])
                temp_path.unlink()
                return False
            
            # Chunk the text
            chunks = chunk_text(
                pdf_text, 
                page_mapping,
                chunk_size=PDF_CONFIG['chunk_size'],
                overlap=PDF_CONFIG['chunk_overlap']
            )
            
            # Create vector store
            model = initialize_gemini()
            vector_store = VectorStore(model_name=VECTOR_CONFIG['embedding_model'])
            vector_store.create_from_chunks(chunks)
            
            # Initialize chat handler
            chat_handler = ChatHandler(model, vector_store)
            
            # Calculate statistics
            processing_time = time.time() - start_time
            stats = {
                'pages': max(page_mapping.values()) if page_mapping else 0,
                'chunks': len(chunks),
                'characters': len(pdf_text),
                'processing_time': processing_time,
            }
            
            # Store in session state
            st.session_state.vector_store = vector_store
            st.session_state.chat_handler = chat_handler
            st.session_state.document_name = uploaded_file.name
            st.session_state.document_stats = stats
            
            # Clean up temp file
            temp_path.unlink()
            
            # Add welcome message
            welcome_msg = f"✅ Successfully analyzed **{uploaded_file.name}** ({stats['pages']} pages, {stats['chunks']} chunks) in {stats['processing_time']:.2f} seconds."
            st.session_state.messages.append({
                "role": "assistant",
                "content": welcome_msg,
                "sources": []
            })
            
            return True
            
    except Exception as e:
        st.error(f"{MESSAGES['error_processing']}{str(e)}")
        if temp_path.exists():
            temp_path.unlink()
        return False

def generate_summary():
    """Generate document summary"""
    if not st.session_state.chat_handler:
        return
    
    with st.spinner("Generating summary..."):
        try:
            summary_query = "Please provide a comprehensive summary of this document, including the main topics covered."
            response, sources = st.session_state.chat_handler.get_response(summary_query, k=5)
            
            st.session_state.messages.append({
                "role": "user",
                "content": "📝 Generate Summary"
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "sources": sources
            })
            st.rerun()
        except Exception as e:
            st.error(f"Error generating summary: {str(e)}")

def reset_conversation():
    """Reset the conversation and clear all data"""
    for key in ['messages', 'vector_store', 'chat_handler', 'document_name', 'document_stats']:
        st.session_state[key] = [] if key == 'messages' else None
    st.session_state.processing = False

def sidebar_content():
    """Sidebar with settings and information"""
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Retrieval mode
        st.session_state.retrieval_mode = st.selectbox(
            "Retrieval Mode",
            ["balanced", "precise", "comprehensive"],
            help="Balanced: 3 chunks | Precise: 2 chunks | Comprehensive: 5 chunks"
        )
        
        # Show sources toggle
        st.session_state.show_sources = st.checkbox(
            "Show Source References",
            value=True,
            help="Display page numbers and snippets with answers"
        )
        
        st.markdown("---")
        
        # Document statistics
        if st.session_state.document_stats:
            st.subheader("📊 Document Stats")
            stats = st.session_state.document_stats
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Pages", stats['pages'])
                st.metric("Chunks", stats['chunks'])
            with col2:
                st.metric("Characters", f"{stats['characters']:,}")
                st.metric("Process Time", f"{stats['processing_time']:.1f}s")
        
        st.markdown("---")
        
        # Actions
        if st.session_state.vector_store:
            st.subheader("🎯 Quick Actions")
            
            if st.button("📝 Generate Summary", use_container_width=True):
                generate_summary()
            
            if st.button("💾 Export Chat", use_container_width=True):
                if st.session_state.messages:
                    chat_text = get_chat_export(st.session_state.messages)
                    st.download_button(
                        "⬇️ Download Chat History",
                        chat_text,
                        file_name="chat_history.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.warning("No messages to export")
            
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 📚 About")
        st.info("""
        **Smart Study Buddy** uses RAG (Retrieval-Augmented Generation) to answer questions from your documents.
        
        **Powered by:**
        - Google Gemini AI
        - Sentence Transformers
        - FAISS Vector Search
        """)

def main():
    # Sidebar
    sidebar_content()
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📚 Smart Study Buddy")
        st.markdown("*Upload your study materials and ask questions. Get intelligent answers with source references.*")
    
    with col2:
        if st.session_state.document_name:
            st.markdown(f"**Current Document:**  \n📄 {st.session_state.document_name}")
            if st.button("🔄 New Document", use_container_width=True):
                reset_conversation()
                st.rerun()
    
    st.markdown("---")
    
    # Main content area
    if not st.session_state.vector_store:
        # Upload section
        st.markdown("### 📤 Upload Your Study Material")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=UI_CONFIG['supported_formats'],
                help=f"Maximum file size: {UI_CONFIG['max_file_size_mb']} MB"
            )
            
            if uploaded_file:
                if st.button("🚀 Process Document", use_container_width=True, type="primary"):
                    success = process_pdf(uploaded_file)
                    if success:
                        st.rerun()
        
        # Features section
        st.markdown("---")
        st.markdown("### ✨ Features")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("#### 🎯 Smart Answers")
            st.write("Get precise answers from your documents")
        with col2:
            st.markdown("#### 📍 Source References")
            st.write("See exactly where info comes from")
        with col3:
            st.markdown("#### 💬 Natural Chat")
            st.write("Ask questions in your own words")
        with col4:
            st.markdown("#### 📝 Summaries")
            st.write("Generate document summaries")
    
    else:
        # Chat interface
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <div><strong>You:</strong></div>
                        <div>{message["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message ai-message">
                        <div><strong>🤖 AI Assistant:</strong></div>
                        <div>{message["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display sources if enabled
                    if st.session_state.show_sources and message.get("sources"):
                        st.markdown(format_sources_for_display(message["sources"]), unsafe_allow_html=True)
        
        # Chat input at the bottom
        st.markdown("---")
        user_input = st.chat_input("Ask a question about your document...", key="chat_input")
        
        if user_input and not st.session_state.processing:
            # Determine k based on retrieval mode
            k_values = {'balanced': 3, 'precise': 2, 'comprehensive': 5}
            k = k_values[st.session_state.retrieval_mode]
            
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response
            st.session_state.processing = True
            
            try:
                with st.spinner("🤔 Thinking..."):
                    response, sources = st.session_state.chat_handler.get_response(user_input, k=k)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ {MESSAGES['error_query']} Error: {str(e)}",
                    "sources": []
                })
            finally:
                st.session_state.processing = False
            
            st.rerun()

if __name__ == "__main__":
    main()
                