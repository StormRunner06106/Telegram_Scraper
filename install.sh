#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  GitHub Location Scraper - Installation"
echo "=========================================="

python3 --version
python3 -m pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env. Add your GitHub token before running the scraper."
else
    echo "Existing .env retained."
fi

chmod +x gscraper.sh install.sh
python3 check_env.py

echo "Installation complete. See README.md, then run: python3 gscraper.py"
