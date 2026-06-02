# 🚀 START HERE - GitHub Scraper Quick Start

## ✅ What You Have

A complete GitHub scraper system with:

- ✅ `.env` file created with your GitHub token
- ✅ Interactive agent mode (`gscraper.py`)
- ✅ 20 predefined US tech hub regions
- ✅ Supabase integration ready
- ✅ Network resilience and auto-resume

## 🎯 Quick Start (3 Steps)

### Step 1: Configure Supabase

```bash
# Check current configuration
python check_env.py
```

You'll see:

- ✅ GITHUB_TOKEN: Already configured!
- ⚠️ SUPABASE_URL: Needs your URL
- ⚠️ SUPABASE_KEY: Needs your key

**Edit .env file:**

```bash
notepad .env        # Windows
nano .env           # Linux/Mac
```

**Get Supabase credentials:**

1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Project Settings** → **API**
4. Copy **Project URL** and **anon/public key**
5. Paste into `.env` file

**Verify:**

```bash
python check_env.py
```

### Step 2: Setup Supabase Tables

```bash
python setup_supabase.py
```

Select:

- **Option 1**: Insert/Update regions (do this first)
- **Option 2**: List regions (verify)

### Step 3: Run Scraper

```bash
python gscraper.py
```

Follow the prompts:

1. Select region (e.g., `1` for Austin, TX)
2. Input limit (e.g., `20` for testing)
3. Press Enter for default filename
4. Watch it scrape!

## 📋 What Happens Next

```
1. Scraper fetches GitHub users from selected region
2. Filters by:
   - Account age (>8 years)
   - GitHub badges (>3)
   - Telegram account exists
3. Checks company (50+ major tech firms)
4. Verifies name matching (GitHub ↔ Telegram)
5. Saves to CSV: {region}_{start}_{end}.csv
6. Tracks progress in state.json
7. Syncs to Supabase in real-time
```

## 🎮 Controls

- **Ctrl+C** - Pause and save progress
- **Y/n** - Confirm prompts
- **Enter** - Accept default

## 📁 Output

**CSV File:**

```csv
link,email,telegramId,blog,years,company,nameMatch
https://github.com/user,email@example.com,@user,blog.com,12,Google,matched
```

**Progress File (state.json):**

```json
{
  "region_id": 1,
  "index": 245,
  "is_end": false,
  "total_processed": 245
}
```

## 🔧 Useful Commands

```bash
# Check environment
python check_env.py

# Setup Supabase
python setup_supabase.py

# Run scraper
python gscraper.py

# Test setup
python test_setup.py

# Check progress
cat state.json
```

## 📚 Documentation

| Document             | Purpose                   |
| -------------------- | ------------------------- |
| `ENV_SETUP.md`       | Detailed .env setup guide |
| `QUICK_REFERENCE.md` | Quick commands            |
| `GSCRAPER_README.md` | Agent mode guide          |
| `SETUP_GUIDE.md`     | Complete setup            |
| `README_MAIN.md`     | Full documentation        |

## ⚠️ Important Notes

### GitHub Token

✅ **Already configured** in your `.env` file!

### Supabase

⚠️ **Needs configuration**:

1. Get credentials from Supabase Dashboard
2. Edit `.env` file
3. Run `python check_env.py` to verify

### States Table

✅ **Already exists** in your Supabase project - will be used as-is

### Regions Table

⚠️ **Needs to be created**:

1. Run `python setup_supabase.py`
2. Select option 1: Insert/Update regions

## 🐛 Troubleshooting

### "SUPABASE_URL: (not set)"

Edit `.env` and add your Supabase project URL

### "SUPABASE_KEY: (not set)"

Edit `.env` and add your Supabase anon key

### "Region already completed"

Use `--no-resume` flag or reset state:

```bash
rm state.json
```

### Rate limit errors

Your GitHub token is already configured, but if you still hit limits:

- Wait for rate limit to reset
- Check token is valid: `python check_env.py`

## ✨ Features

- 🔄 Auto-resume from where you left off
- 🔌 Network resilience (auto-retry)
- 💾 Supabase real-time sync
- 🏢 Company detection (50+ companies)
- ✅ Name verification (GitHub ↔ Telegram)
- 📊 Progress tracking every 10 users
- 🛑 Graceful Ctrl+C handling

## 🎯 Next Steps

1. ✅ Check environment: `python check_env.py`
2. ⚠️ Edit `.env` with Supabase credentials
3. ✅ Verify: `python check_env.py`
4. ✅ Setup Supabase: `python setup_supabase.py`
5. ✅ Run scraper: `python gscraper.py`

## 💡 Tips

- Start with limit=20 for testing
- Use Ctrl+C to pause anytime
- Check `state.json` for progress
- Files are named with index ranges
- Resume works automatically

## 📞 Need Help?

1. Run `python check_env.py` - Check configuration
2. Run `python test_setup.py` - Verify installation
3. Read `ENV_SETUP.md` - Detailed .env guide
4. Read `SETUP_GUIDE.md` - Complete setup guide
5. Read `QUICK_REFERENCE.md` - Quick commands

---

**Ready to start?**

```bash
# 1. Configure Supabase
python check_env.py
notepad .env        # Edit with your credentials
python check_env.py # Verify

# 2. Setup database
python setup_supabase.py
# Select option 1

# 3. Run scraper
python gscraper.py
```

🚀 **Let's scrape!**
