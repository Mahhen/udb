#!/bin/bash

# Smart Study Buddy - Quick Start Script

echo "🚀 Starting Smart Study Buddy..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Please edit .env and add your GEMINI_API_KEY"
    echo "Get your key from: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Press Enter after adding your API key..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

# Run the app
echo ""
echo "✨ Launching Smart Study Buddy..."
echo "🌐 The app will open in your browser at http://localhost:8501"
echo ""

streamlit run app.py
