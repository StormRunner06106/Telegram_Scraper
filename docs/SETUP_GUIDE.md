# Complete Setup Guide

## Prerequisites

- Python 3.10 or higher
- Internet connection
- GitHub account (for token)
- Supabase account (optional, for sync)

## Step-by-Step Setup

### 1. Install Python Dependencies

#### Option A: With Supabase (Recommended)

```bash
pip install supabase
```

#### Option B: Without Supabase

No installation needed! The scraper works with Python standard library only.

### 2. Get GitHub Token (Recommended)

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: "GitHub Scraper"
4. Select scopes: `public_repo`, `read:user`
5. Click "Generate token"
6. Copy the token (starts with `ghp_` or `github_pat_`)

### 3. Setup Supabase (Optional)

#### Create Supabase Project

1. Go to https://supabase.com
2. Sign up / Log in
3. Click "New Project"
4. Fill in:
   - Name: `github-scraper`
   - Database Password: (generate strong password)
   - Region: (choose closest to you)
5. Wait for project to be ready (~2 minutes)

#### Get Supabase Credentials

1. Go to Project Settings → API
2. Copy:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGc...` (long string)

#### Create Tables

**Option A: Using Setup Script (Easiest)**

```bash
# Set environment variables
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="eyJhbGc..."

# Run setup script
python setup_supabase.py

# Select option 6 to see SQL
# Then select option 1 to insert regions
```

**Option B: Manual SQL**

1. Go to Supabase Dashboard → SQL Editor
2. Click "New Query"
3. Paste this SQL:

```sql
-- Regions table
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_regions_name ON regions(name);
```

**Note**: The States table already exists in your Supabase project and will be used as-is.

4. Click "Run"
5. Insert regions using setup script:

```bash
python setup_supabase.py
# Select option 1
```

### 4. Configure Environment Variables

#### Windows (PowerShell)

```powershell
# Temporary (current session only)
$env:GITHUB_TOKEN="your-github-token"
$env:SUPABASE_URL="https://xxxxx.supabase.co"
$env:SUPABASE_KEY="your-supabase-key"

# Permanent (add to PowerShell profile)
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'your-token', 'User')
[System.Environment]::SetEnvironmentVariable('SUPABASE_URL', 'your-url', 'User')
[System.Environment]::SetEnvironmentVariable('SUPABASE_KEY', 'your-key', 'User')
```

#### Windows (CMD)

```cmd
REM Temporary
set GITHUB_TOKEN=your-github-token
set SUPABASE_URL=https://xxxxx.supabase.co
set SUPABASE_KEY=your-supabase-key

REM Permanent (System Properties → Environment Variables)
setx GITHUB_TOKEN "your-github-token"
setx SUPABASE_URL "https://xxxxx.supabase.co"
setx SUPABASE_KEY "your-supabase-key"
```

#### Linux/Mac (Bash)

```bash
# Temporary (current session)
export GITHUB_TOKEN="your-github-token"
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="your-supabase-key"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export GITHUB_TOKEN="your-github-token"' >> ~/.bashrc
echo 'export SUPABASE_URL="https://xxxxx.supabase.co"' >> ~/.bashrc
echo 'export SUPABASE_KEY="your-supabase-key"' >> ~/.bashrc
source ~/.bashrc
```

### 5. Verify Setup

```bash
# Test GitHub token
python -c "import os; print('GitHub token:', 'SET' if os.getenv('GITHUB_TOKEN') else 'NOT SET')"

# Test Supabase connection
python -c "from supabase import create_client; import os; client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); print('Supabase: Connected')"

# List regions
python setup_supabase.py
# Select option 2
```

### 6. Run Your First Scrape

```bash
# Windows
python gscraper.py

# Linux/Mac
python3 gscraper.py
# or
chmod +x gscraper.sh
./gscraper.sh
```

Follow the prompts:

1. Select region (e.g., `1` for Austin, TX)
2. Enter limit (e.g., `20` for testing)
3. Press Enter for default filename
4. Watch it scrape!

## Verification Checklist

- [ ] Python 3.10+ installed
- [ ] `supabase` package installed (optional)
- [ ] GitHub token obtained and set
- [ ] Supabase project created (optional)
- [ ] Supabase tables created (optional)
- [ ] Regions inserted into Supabase (optional)
- [ ] Environment variables set
- [ ] Test scrape completed successfully

## Common Issues

### "ModuleNotFoundError: No module named 'supabase'"

```bash
pip install supabase
```

### "Supabase not configured"

Set environment variables:

```bash
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"
```

### "GitHub API rate limit exceeded"

Set GitHub token:

```bash
export GITHUB_TOKEN="your-token"
```

### "relation 'regions' does not exist"

Create tables using setup script or manual SQL (see Step 3).

### "Network disconnected"

GScraper will wait automatically. Just leave it running.

## Next Steps

1. **Test with small limit**: Start with 20 users
2. **Verify output**: Check CSV file quality
3. **Monitor progress**: Use `python setup_supabase.py` → option 3
4. **Scale up**: Increase limit to 1000
5. **Automate**: Create scripts for multiple regions

## Support

- Check `GSCRAPER_README.md` for usage examples
- Check `USAGE_EXAMPLES.md` for github_scraper.py examples
- Check `CHANGELOG.md` for recent updates

## Quick Reference

```bash
# Run scraper
python gscraper.py

# Setup Supabase
python setup_supabase.py

# Old scraper (manual)
python github_scraper.py list
python github_scraper.py region 1

# Check state
cat state.json

# Reset state
rm state.json
```
