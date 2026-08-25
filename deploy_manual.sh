#!/bin/bash

# Manual deployment script for HoopSync to TrialSync repository
# This script provides guidance for manual authentication

echo "🏀 HoopSync Manual Deployment to TrialSync"
echo "=========================================="
echo ""

# Check current git status
echo "Current git status:"
git status
echo ""

# Show current remote
echo "Current git remote:"
git remote -v
echo ""

echo "The code has been committed locally. To push to GitHub, you need to authenticate."
echo ""
echo "Choose your authentication method:"
echo ""
echo "1. Personal Access Token (Recommended):"
echo "   git remote set-url origin https://YOUR_TOKEN@github.com/donbassofficial-hub/TrialSync.git"
echo "   git push -u origin main"
echo ""
echo "2. SSH Key Setup:"
echo "   git remote set-url origin git@github.com:donbassofficial-hub/TrialSync.git"
echo "   git push -u origin main"
echo "   (Make sure your SSH key is added to GitHub account)"
echo ""
echo "3. GitHub CLI (if installed):"
echo "   gh auth login"
echo "   git push -u origin main"
echo ""
echo "To create a Personal Access Token:"
echo "1. Go to https://github.com/settings/tokens"
echo "2. Click 'Generate new token (classic)'"
echo "3. Select scopes: repo (full control of private repositories)"
echo "4. Generate and copy the token"
echo "5. Use it in the command above"
echo ""
echo "After successful push, your HoopSync will be available at:"
echo "https://github.com/donbassofficial-hub/TrialSync"
