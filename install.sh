#!/bin/bash
# Installation script for GitHub Scraper

echo "=========================================="
echo "  GitHub Scraper - Installation"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi
echo "✅ Python found"
echo ""

# Install dependencies
echo "Installing dependencies..."
read -p "Install Supabase support? (Y/n): " install_supabase

if [ "$install_supabase" != "n" ] && [ "$install_supabase" != "N" ]; then
    pip3 install supabase
    if [ $? -eq 0 ]; then
        echo "✅ Supabase installed"
    else
        echo "⚠️  Supabase installation failed (optional)"
    fi
else
    echo "⏭️  Skipping Supabase installation"
fi
echo ""

# Create .env file
echo "Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env with your credentials"
else
    echo "⏭️  .env already exists"
fi
echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x gscraper.sh
chmod +x install.sh
echo "✅ Scripts are executable"
echo ""

# Run setup test
echo "Running setup test..."
python3 test_setup.py
echo ""

echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: python3 setup_supabase.py (optional)"
echo "  3. Run: python3 gscraper.py"
echo ""
echo "Documentation:"
echo "  - README_MAIN.md - Main documentation"
echo "  - QUICK_REFERENCE.md - Quick commands"
echo "  - SETUP_GUIDE.md - Detailed setup"
echo ""
