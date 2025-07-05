#!/bin/bash
# Start script for Nigerian School Result Portal

echo "🚀 Starting Nigerian School Result Portal..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r backend/requirements.txt

# Initialize database if needed
if [ ! -f "backend/school_portal.db" ]; then
    echo "🗄️ Initializing database..."
    cd backend && python init_db.py && cd ..
fi

# Start the application
echo "🌟 Starting application on port ${PORT:-5000}..."
python app.py

