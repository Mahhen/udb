# 📚 Smart Study Buddy - Python RAG Implementation

An AI-powered study assistant that uses Retrieval-Augmented Generation (RAG) to answer questions from your PDF documents with source references.

## ✨ Features

- **📄 PDF Processing**: Upload and analyze PDF documents
- **🤖 Smart Q&A**: Ask questions in natural language
- **📍 Source References**: Get answers with page numbers and snippets
- **💬 Conversational**: Maintains context throughout the session
- **⚡ Fast Search**: Uses FAISS vector database for efficient retrieval
- **🎯 Accurate**: Powered by Google's Gemini AI with sentence transformers

## 🏗️ Architecture

```
User Query → Vector Store (FAISS) → Top-K Retrieval → Context
                                                          ↓
                                                   Gemini LLM
                                                          ↓
                                              Answer + Sources
```

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **LLM**: Google Gemini API (gemini-1.5-flash)
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Vector Store**: FAISS
- **PDF Processing**: PyMuPDF

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Google Gemini API key

### Setup Steps

1. **Clone or download the project**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
cp .env.example .env

# Add your Gemini API key to .env
# Get your key from: https://makersuite.google.com/app/apikey
```

4. **Run the application**
```bash
streamlit run app.py
```

5. **Open in browser**
   - The app will automatically open at `http://localhost:8501`

## 🚀 Usage

1. **Upload a PDF**: Click the file uploader and select your study material
2. **Wait for processing**: The app will extract text and create embeddings
3. **Ask questions**: Type your questions in the chat interface
4. **View answers**: Get AI-generated answers with source page references

### Example Questions

- "What is the main concept explained in this document?"
- "Summarize the section about [topic]"
- "What does the author say about [specific concept]?"
- "Explain the difference between [concept A] and [concept B]"

## 📁 Project Structure

```
smart-study-buddy/
├── app.py                 # Main Streamlit application
├── pdf_processor.py       # PDF text extraction and chunking
├── vector_store.py        # FAISS vector store implementation
├── chat_handler.py        # RAG logic and prompt engineering
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## 🔧 Configuration

### Chunk Settings
Edit in `pdf_processor.py`:
```python
chunk_size = 1000      # Characters per chunk
overlap = 200          # Overlap between chunks
```

### Retrieval Settings
Edit in `chat_handler.py`:
```python
k = 3                  # Number of chunks to retrieve
max_context_length = 3000  # Max context characters
```

### Model Selection
Edit in `vector_store.py`:
```python
model_name = 'all-MiniLM-L6-v2'  # Embedding model
```

## 🎯 How RAG Works

1. **Document Processing**
   - PDF is uploaded and text is extracted
   - Text is split into overlapping chunks (~1000 chars)
   - Each chunk retains page number metadata

2. **Embedding Creation**
   - Each chunk is converted to a vector using Sentence Transformers
   - Vectors are stored in FAISS index for fast similarity search

3. **Query Processing**
   - User's question is converted to a vector
   - FAISS finds the top-K most similar chunks
   - Relevant chunks are retrieved with page numbers

4. **Answer Generation**
   - Retrieved context + user question → sent to Gemini
   - Gemini generates answer based only on provided context
   - Sources (page numbers) are displayed with the answer

## 🔒 Privacy & Data

- All processing happens locally except LLM calls
- PDFs are temporarily stored during processing
- No data is permanently stored after session ends
- Only relevant text chunks are sent to Gemini API

## 🐛 Troubleshooting

### "Could not extract text from PDF"
- Ensure your PDF is text-based (not scanned images)
- Try using OCR software first if needed

### "GEMINI_API_KEY not set"
- Create a `.env` file in the project root
- Add: `GEMINI_API_KEY=your_key_here`

### Slow processing
- Large PDFs take longer to process
- First-time model download may be slow
- Consider reducing `chunk_size` for faster indexing

### Out of memory
- Close other applications
- Reduce PDF size or split into smaller documents
- Lower `k` value in retrieval settings

## 🚀 Deployment

### Deploy to Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Add `GEMINI_API_KEY` to secrets
5. Deploy!

### Local Production

```bash
# Install production server
pip install gunicorn

# Run with optimizations
streamlit run app.py --server.port=8501 --server.headless=true
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Support for multiple documents
- [ ] OCR for scanned PDFs
- [ ] Export chat history
- [ ] Better UI/UX
- [ ] Support for other file formats (DOCX, TXT)
- [ ] Chat history persistence
- [ ] Summary generation

## 📄 License

MIT License - feel free to use for your projects!

## 🙏 Credits

- **Streamlit** - Web framework
- **Google Gemini** - LLM
- **Sentence Transformers** - Embeddings
- **FAISS** - Vector search
- **PyMuPDF** - PDF processing

## 📞 Support

For issues or questions:
- Check the troubleshooting section
- Review Gemini API docs: [ai.google.dev](https://ai.google.dev)
- Check FAISS docs: [github.com/facebookresearch/faiss](https://github.com/facebookresearch/faiss)

---

**Happy Studying! 📚✨**
