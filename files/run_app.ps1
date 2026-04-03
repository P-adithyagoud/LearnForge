# run_app.ps1 - Start the integrated LearnForge application
Write-Host "🔧 Preparing LearnForge environment..." -ForegroundColor Cyan

# Check if Python is installed
try {
    python --version
} catch {
    Write-Error "❌ Python is not found. Please install Python 3.14 or later."
    exit
}

# Install dependencies if not already present
Write-Host "📦 Ensuring dependencies are installed..." -ForegroundColor Cyan
pip install -q fastapi uvicorn httpx pyjwt python-multipart python-dotenv

# Start the integrated FastAPI application
Write-Host "🚀 Starting integrated application on http://localhost:8000" -ForegroundColor Green
Write-Host "   Frontend & Backend are now connected on the same port." -ForegroundColor Gray
Write-Host "   Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

uvicorn api.index:app --reload --port 8000
