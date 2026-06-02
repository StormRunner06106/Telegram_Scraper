#!/bin/bash
# GScraper launcher for Linux/Mac

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Run gscraper
python3 gscraper.py
