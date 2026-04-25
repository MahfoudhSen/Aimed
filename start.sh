#!/bin/bash
set -e

echo "🏠 SafeNest AI — Starting..."

# Check for .env
if [ ! -f ".env" ]; then
  if [ -f ".env.template" ]; then
    echo "⚠️  No .env file found. Copying from .env.template..."
    cp .env.template .env
    echo "👉  Edit .env and add your ANTHROPIC_API_KEY, then re-run this script."
    exit 1
  fi
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip3 install -r requirements.txt
fi

echo "✅ Starting SafeNest AI on http://localhost:8000"
echo "   Press Ctrl+C to stop."
echo ""

cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
