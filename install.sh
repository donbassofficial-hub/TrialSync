#!/bin/bash

# HoopSync Installation Script

echo "🏀 HoopSync Installation"
echo "======================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || python --version
if [ $? -ne 0 ]; then
    echo "❌ Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found"
echo ""

# Create virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv venv || python -m venv venv
if [ $? -ne 0 ]; then
    echo "⚠️  Could not create virtual environment, continuing with system Python..."
else
    echo "✅ Virtual environment created"
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate || venv\Scripts\activate
    echo "✅ Virtual environment activated"
fi

echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p data logs models/templates
echo "✅ Directories created"
echo ""

# Make executable script executable
chmod +x run_hoopsync

echo ""
echo "🎉 Installation complete!"
echo ""
echo "To run HoopSync:"
echo "  ./run_hoopsync --help"
echo ""
echo "Or with Python directly:"
echo "  python -m hoopsync.main --help"
echo ""
echo "For first-time setup, test video capture:"
echo "  python -m hoopsync.main --test-capture"
