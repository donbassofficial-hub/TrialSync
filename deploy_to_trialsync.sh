#!/bin/bash

# Deployment script to push HoopSync to TrialSync repository

echo "🏀 HoopSync Deployment to TrialSync Repository"
echo "=============================================="

# Check if git is initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
else
    echo "Git repository already initialized"
fi

# Add remote repository
echo "Adding TrialSync remote repository..."
git remote add origin https://github.com/donbassofficial-hub/TrialSync.git 2>/dev/null || \
git remote set-url origin https://github.com/donbassofficial-hub/TrialSync.git

# Stage all files
echo "Staging files..."
git add .

# Create initial commit
echo "Creating initial commit..."
git commit -m "Initial commit: HoopSync NBA 2K Statistics Pipeline

- Complete computer vision pipeline for NBA 2K gameplay analysis
- Frame capture from Elgato HD60 X
- Screen detection and ROI extraction
- OCR-based statistics parsing
- Local database with deduplication
- Live web dashboard
- Cloud synchronization support
- Comprehensive configuration and documentation

Generated with [Devin](https://devin.ai)

Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>"

# Push to repository
echo "Pushing to TrialSync repository..."
git push -u origin main

echo ""
echo "✅ Deployment complete!"
echo "📦 HoopSync is now available at: https://github.com/donbassofficial-hub/TrialSync"
echo ""
echo "To install and run:"
echo "  git clone https://github.com/donbassofficial-hub/TrialSync.git"
echo "  cd TrialSync"
echo "  pip install -r requirements.txt"
echo "  python -m hoopsync.main --help"
