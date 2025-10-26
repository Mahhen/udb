import streamlit as st
import google.generativeai as genai
from pathlib import Path
import os
from pdf_processor import extract_text_from_pdf, chunk_text
from vector_store import VectorStore
from chat_handler import ChatHandler
from dotenv import load_dotenv

st.set_page_config(
    page_title="Smart Study Buddy",
    
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #000000;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
    }
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
        background-color: #f8f9fa;
        border: 2px solid #e5e7eb;
        align-self: flex-start;
        margin-right: 20%;
    }
    .source-reference {
        background-color: #e0f2fe;
        padding: 0.75rem;
        border-left: 4px solid #3b82f6;
        margin-top: 0.5rem;
        font-size: 0.85rem;
        border-radius: 0.25rem;
    }
    /* Make file uploader more visible */
    .stFileUploader {
        background-color: #ffffff;
        border: 3px dashed #3b82f6;
        border-radius: 1rem;
        padding: 2rem;
    }
    .stFileUploader > div {
        background-color: #ffffff;
    }
    /* Improve button visibility */
    .stButton > button {
        font-weight: 600;
        font-size: 1.1rem;
        padding: 0.75rem 2rem;
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'chat_handler' not in st.session_state:
    st.session_state.chat_handler = None
if 'document_name' not in st.session_state:
    st.session_state.document_name = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

def initialize_gemini():
    """Initialize Gemini API"""
    load_dotenv()

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("Please set GEMINI_API_KEY in your .env file")
        st.stop()

    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def process_pdf(uploaded_file):
    """Process uploaded PDF and create vector store"""
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
            
            welcome_msg = f"I've finished analyzing **{uploaded_file.name}**. Feel free to ask any questions about its content!"
            st.session_state.messages.append({
                "role": "assistant",
                "content": welcome_msg,
                "sources": []
            })
            
            return True
            
    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")
        if temp_path.exists():
            temp_path.unlink()
        return False

def reset_conversation():
    """Reset the conversation and clear all data"""
    st.session_state.messages = []
    st.session_state.vector_store = None
    st.session_state.chat_handler = None
    st.session_state.document_name = None
    st.session_state.processing = False

def main():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Smart Study Buddy")
        st.markdown("*Upload your study materials and ask questions. Get intelligent answers with source references.*")
    
    with col2:
        if st.session_state.document_name:
            st.markdown(f"**Current Document:**  \n📄 {st.session_state.document_name}")
            if st.button("New Document", use_container_width=True):
                reset_conversation()
                st.rerun()
    
    st.markdown("---")
    
    if not st.session_state.vector_store:
        st.markdown("### 📤 Upload Your Study Material")
        st.markdown("") 
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.markdown("""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 3rem; border-radius: 1rem; text-align: center; 
                            box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin: 2rem 0;'>
                    <h2 style='color: white; margin-bottom: 1rem;'>📚 Get Started</h2>
                    <p style='color: rgba(255,255,255,0.9); font-size: 1.1rem;'>
                        Upload a PDF document and start asking questions!
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=['pdf'],
                help="Upload your notes, textbooks, or study materials in PDF format",
                label_visibility="collapsed"
            )
            
            if uploaded_file:
                st.success(f"File loaded: **{uploaded_file.name}**")
                st.info(f"📊 Size: {uploaded_file.size / 1024:.1f} KB")
                
                if st.button("Process Document", use_container_width=True, type="primary"):
                    success = process_pdf(uploaded_file)
                    if success:
                        st.rerun()
        
        st.markdown("---")
        st.markdown("### ✨ What You Can Do")
        st.markdown("")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
                <div style='background: white; padding: 1.5rem; border-radius: 0.75rem; 
                            border: 2px solid #e5e7eb; height: 180px;'>
                    <h3 style='color: #3b82f6; margin-bottom: 0.5rem;'>🎯 Smart Answers</h3>
                    <p style='color: #6b7280;'>Get precise answers directly from your uploaded documents with AI-powered understanding</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div style='background: white; padding: 1.5rem; border-radius: 0.75rem; 
                            border: 2px solid #e5e7eb; height: 180px;'>
                    <h3 style='color: #3b82f6; margin-bottom: 0.5rem;'>📍 Source References</h3>
                    <p style='color: #6b7280;'>See exactly which page and section your answer comes from for verification</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
                <div style='background: white; padding: 1.5rem; border-radius: 0.75rem; 
                            border: 2px solid #e5e7eb; height: 180px;'>
                    <h3 style='color: #3b82f6; margin-bottom: 0.5rem;'>💬 Natural Chat</h3>
                    <p style='color: #6b7280;'>Ask questions in your own words, just like talking to a study partner</p>
                </div>
            """, unsafe_allow_html=True)
    
    else:
        st.markdown("""
            <div style='background: linear-gradient(to right, #3b82f6, #8b5cf6); 
                        padding: 1rem; border-radius: 0.5rem; margin-bottom: 1.5rem;'>
                <h3 style='color: white; margin: 0;'>💬 Chat with Your Document</h3>
            </div>
        """, unsafe_allow_html=True)
        
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <div style='font-weight: 600; margin-bottom: 0.5rem;'> You:</div>
                        <div>{message["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message ai-message">
                        <div style='font-weight: 600; margin-bottom: 0.5rem; color: #000000;'>AI Assistant:</div>
                        <div style='color: #1f2937;'>{message["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if message.get("sources"):
                        sources_html = "<div class='source-reference'><strong>Sources:</strong><br>"
                        for source in message["sources"]:
                            sources_html += f"• <strong>Page {source['page']}:</strong> \"{source['text'][:100]}...\"<br>"
                        sources_html += "</div>"
                        st.markdown(sources_html, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.chat_input("Ask a question about your document...", key="chat_input")
        with col2:
            if st.button("🗑️Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        if user_input and not st.session_state.processing:
            st.session_state.messages.append({
                "role": "user",
                "content": user_input
            })
            
            st.session_state.processing = True
            
            try:
                with st.spinner("Thinking..."):
                    response, sources = st.session_state.chat_handler.get_response(user_input)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error: {str(e)}",
                    "sources": []
                })
            finally:
                st.session_state.processing = False
            
            st.rerun()

if __name__ == "__main__":
    main()