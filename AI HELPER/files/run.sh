#!/bin/bash
# ══════════════════════════════════════════
# LearnForge — Setup & Run Script
# ══════════════════════════════════════════

set -e

echo "🔧 Setting up LearnForge..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install it first."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q fastapi uvicorn httpx pyjwt python-multipart python-dotenv

# Set your Groq API key here or export it before running
if [ -z "$GROQ_API_KEY" ]; then
    echo ""
    echo "⚠️  GROQ_API_KEY is not set!"
    echo "   Get your free key at: https://console.groq.com"
    echo "   Then run: export GROQ_API_KEY=your_key_here"
    echo ""
    read -p "   Enter your Groq API key (or press Enter to skip): " key
    if [ -n "$key" ]; then
        export GROQ_API_KEY="$key"
    fi
fi

# Create DB directory
mkdir -p backend

# Start FastAPI backend
echo ""
echo "🚀 Starting backend on http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""

# Run from current directory since main.py is here
GROQ_API_KEY="$GROQ_API_KEY" uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Serve frontend from current directory
echo "🌐 Starting frontend on http://localhost:3000"
echo ""
python3 -m http.server 3000 &
FRONTEND_PID=$!

echo "════════════════════════════════════════"
echo "  ✅ LearnForge is running!"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Demo credentials:"
echo "    Email:    demo@learn.ai"
echo "    Password: demo123"
echo ""
echo "  Press Ctrl+C to stop"
echo "════════════════════════════════════════"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
