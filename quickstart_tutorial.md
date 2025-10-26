# ⚡ Quick Start - Smart Study Buddy

Get up and running in **5 minutes**!

## 🎯 What You'll Need

- **Python 3.9+** installed on your computer
- **5 minutes** of your time
- **A Gemini API key** (free - we'll get this)

---

## 📝 Step 1: Get Your Gemini API Key (2 minutes)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Get API Key"** or **"Create API Key"**
4. Copy the key (starts with `AIza...`)

**Keep this key safe - you'll need it in Step 3!**

---

## 💻 Step 2: Download and Setup (1 minute)

### Option A: Using the Quick Start Script (Easiest)

```bash
# Download and extract the project
cd smart-study-buddy

# Make the script executable
chmod +x run.sh

# Run it!
./run.sh
```

The script will:
- ✅ Create a virtual environment
- ✅ Install all dependencies
- ✅ Prompt you for your API key
- ✅ Launch the app

### Option B: Manual Setup

```bash
# 1. Navigate to project directory
cd smart-study-buddy

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## 🔑 Step 3: Add Your API Key (30 seconds)

Create a file named `.env` in the project folder:

```bash
# Copy the example file
cp .env.example .env

# Edit it (use your favorite editor)
nano .env
```

Add your API key:
```
GEMINI_API_KEY=AIza...your_key_here
```

Save and close (Ctrl+X, then Y, then Enter in nano)

---

## 🚀 Step 4: Launch the App (30 seconds)

```bash
streamlit run app.py
```

The app will automatically open in your browser at `http://localhost:8501`

**You're done!** 🎉

---

## 🧪 Step 5: Try It Out (1 minute)

1. **Upload a PDF**
   - Click the upload button
   - Select any PDF from your computer
   - Wait a few seconds for processing

2. **Ask a Question**
   - Type something like: "What is this document about?"
   - Press Enter
   - Get your AI-powered answer with page references!

---

## 💡 Example Questions to Try

Once you've uploaded a document, try these:

- `"Summarize this document in 3 sentences"`
- `"What are the main topics covered?"`
- `"Explain [specific concept] from the document"`
- `"What does page 5 discuss?"`
- `"What's the difference between [topic A] and [topic B]?"`

---

## 🎓 Pro Tips

### Get Better Answers

1. **Be specific**: Instead of "Tell me about X", try "What does the author say about X in chapter 2?"

2. **Reference pages**: "What information is on page 10?"

3. **Compare concepts**: "How does concept A differ from concept B?"

### Use Advanced Features (Enhanced Version)

If using `enhanced_app.py`:

1. **Generate Summary**
   - Click "📝 Generate Summary" in sidebar

2. **Export Chat**
   - Click "💾 Export Chat" to save your conversation

3. **Change Retrieval Mode**
   - Try different modes for different results:
     - **Balanced**: Good for most questions (default)
     - **Precise**: When you want exact info
     - **Comprehensive**: For broad questions

---

## 🔧 Troubleshooting

### "GEMINI_API_KEY not set"
- Make sure you created the `.env` file
- Check that you copied the full API key
- Restart the app

### "Could not extract text from PDF"
- Your PDF might be scanned (images)
- Try a different PDF with selectable text
- Use OCR software first to convert scanned PDFs

### "Port already in use"
```bash
# Kill the existing process
lsof -ti:8501 | xargs kill -9
# Or just close the terminal and open a new one
```

### Slow Processing
- Large PDFs take longer (normal!)
- First run downloads ML models (~500MB)
- Subsequent runs are much faster

### "Module not found"
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 🎯 What's Next?

### Learn More
- Read the full [README.md](README.md) for features
- Check [DEPLOYMENT.md](DEPLOYMENT.md) to deploy online
- Run tests: `python test_app.py`

### Customize
- Edit `config.py` to change settings
- Adjust chunk size, retrieval count, etc.
- Modify prompts in `chat_handler.py`

### Share Your Project
- Deploy to Streamlit Cloud (free!)
- Share with friends and classmates
- Contribute improvements on GitHub

---

## 📊 Quick Performance Guide

### Document Size Limits

| Document Size | Processing Time | Recommended |
|--------------|----------------|-------------|
| < 10 pages   | 5-10 seconds   | ✅ Great     |
| 10-50 pages  | 15-30 seconds  | ✅ Good      |
| 50-100 pages | 30-60 seconds  | ⚠️ OK       |
| > 100 pages  | 1-2 minutes    | ⚠️ Slow     |

**Tip**: For very large documents, consider splitting them into chapters.

---

## 🆘 Still Need Help?

1. **Check the error message** - it usually tells you what's wrong
2. **Google the error** - someone else probably had the same issue
3. **Check the logs** - look in terminal for detailed errors
4. **Try with a different PDF** - isolate the problem

### Common Error Messages Decoded

| Error | Meaning | Solution |
|-------|---------|----------|
| "API key not found" | .env file missing/wrong | Create .env with your key |
| "No module named..." | Dependency not installed | Run `pip install -r requirements.txt` |
| "Port in use" | Another app using 8501 | Kill the process or use different port |
| "Out of memory" | PDF too large | Try smaller PDF or increase RAM |

---

## 🎉 You're All Set!

Now you have an AI study assistant that can:
- ✅ Read and understand PDFs
- ✅ Answer questions about content
- ✅ Provide page references
- ✅ Generate summaries
- ✅ Chat naturally about your documents

**Happy studying! 📚✨**

---

## 📖 Quick Command Reference

```bash
# Start the app
streamlit run app.py

# Use enhanced version
streamlit run enhanced_app.py

# Run tests
python test_app.py

# Update dependencies
pip install -r requirements.txt --upgrade

# Clear cache
streamlit cache clear

# Stop the app
Ctrl+C (in terminal)
```

---

**Next:** Ready to customize? Check out [README.md](README.md) for advanced usage!
