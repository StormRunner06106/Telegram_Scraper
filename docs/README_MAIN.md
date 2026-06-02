# 🔍 GitHub Scraper - Complete System

> Network-resilient GitHub user scraper with Telegram verification, company detection, and Supabase sync

## 🚀 Quick Start (3 Steps)

```bash
# 1. Test setup
python test_setup.py

# 2. Run interactive scraper
python gscraper.py

# 3. Follow prompts and start scraping!
```

## ✨ Features

- 🔄 **Auto-resume** - Never lose progress
- 🔌 **Network resilience** - Handles disconnections automatically
- 💾 **Supabase sync** - Real-time state synchronization
- 🎯 **Smart filtering** - Age, badges, Telegram, company
- 🏢 **Company detection** - 50+ major tech companies
- ✅ **Name verification** - Cross-platform identity matching
- 📊 **Progress tracking** - Detailed state management
- 🛑 **Graceful shutdown** - Ctrl+C to pause safely

## 📋 What It Does

1. **Searches GitHub** users by location (20 US tech hubs)
2. **Filters by**:
   - Account age (>8 years)
   - GitHub badges (>3)
   - Telegram account exists
   - Company (optional: major tech firms)
3. **Verifies identity** by comparing GitHub and Telegram names
4. **Saves to CSV** with all data points
5. **Tracks progress** for resume capability

## 📊 Output Example

```csv
link,email,telegramId,blog,years,company,nameMatch
https://github.com/user1,user@email.com,@user1,blog.com,12,Google,matched
https://github.com/user2,,@user2,,15,Microsoft,not matched
https://github.com/user3,user3@email.com,@user3,,10,,unknown
```

## 🎯 Two Modes

### 1. Agent Mode (Recommended)

**Interactive, resilient, auto-recovery**

```bash
python gscraper.py
```

Features:

- Step-by-step CLI
- Network auto-retry
- Supabase sync
- Smart file naming
- Graceful Ctrl+C

### 2. CLI Mode

**Quick, scriptable, direct control**

```bash
# List regions
python github_scraper.py list

# Scrape by region
python github_scraper.py region 1 --max-results 100

# Scrape by location
python github_scraper.py scrape "Austin, Texas"
```

## 📁 Project Files

| File                | Purpose                   |
| ------------------- | ------------------------- |
| `gscraper.py`       | Interactive agent scraper |
| `github_scraper.py` | CLI scraper               |
| `setup_supabase.py` | Database setup            |
| `test_setup.py`     | Verify installation       |
| `regions.json`      | 20 predefined regions     |
| `state.json`        | Progress tracking (auto)  |

## 📚 Documentation

| Document             | Description                 |
| -------------------- | --------------------------- |
| `SETUP_GUIDE.md`     | Complete setup instructions |
| `GSCRAPER_README.md` | Agent mode guide            |
| `USAGE_EXAMPLES.md`  | CLI mode examples           |
| `PROJECT_SUMMARY.md` | Full project overview       |
| `CHANGELOG.md`       | Version history             |

## ⚙️ Setup

### Minimum Requirements

- Python 3.10+
- Internet connection

### Recommended Setup

```bash
# 1. Install dependencies
pip install supabase

# 2. Set environment variables
export GITHUB_TOKEN="your_token"
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="your_key"

# 3. Setup Supabase (optional)
python setup_supabase.py

# 4. Test setup
python test_setup.py

# 5. Run scraper
python gscraper.py
```

See `SETUP_GUIDE.md` for detailed instructions.

## 🌍 Regions (20 US Tech Hubs)

Austin, San Francisco, New York, Seattle, Boston, Los Angeles, Chicago, Denver, Portland, Miami, Atlanta, Dallas, San Diego, Phoenix, Philadelphia, Washington DC, Raleigh, Salt Lake City, Minneapolis, Nashville

## 🏢 Detected Companies (50+)

Apple, Google, Microsoft, Amazon, Meta, Netflix, NVIDIA, Tesla, SpaceX, Twitter, Uber, Airbnb, Stripe, Salesforce, Oracle, IBM, Intel, AMD, and 35+ more

## 📈 Performance

- **Search improvement**: 585x more results (flexible matching)
- **Speed**: ~1 user/second (with delay)
- **Capacity**: ~3,600 users/hour
- **Rate limits**: 5,000/hour with token

## 🔧 Configuration

### Environment Variables

```bash
# Required for higher limits
GITHUB_TOKEN=your_github_token

# Optional for Supabase sync
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
```

### Delay Settings

Default: 1 second between requests (configurable)

## 🎮 Usage Examples

### Interactive Mode

```bash
$ python gscraper.py

🔍 GitHub Scraper Agent
Network-resilient scraping with auto-resume

📍 Available Regions:
ID    Name                           State
1     Austin, TX                     Texas
2     San Francisco, CA              California
...

👉 Enter region ID: 1
✓ Selected: Austin, TX
   Continue? (Y/n): Y

📊 Data Limit
👉 Enter limit: 100
✓ Limit set to: 100
   Continue? (Y/n): Y

💾 Output Filename
👉 Enter filename: [Enter for default]
✓ Output file: Austin_TX_0.csv
   Continue? (Y/n): Y

🚀 Starting scraper agent...
```

### CLI Mode

```bash
# List regions and progress
python github_scraper.py list

# Scrape region 1 (Austin)
python github_scraper.py region 1 --max-results 100 --delay 1

# Scrape custom location
python github_scraper.py scrape "Boulder, Colorado" --max-results 50
```

## 🛑 Pause and Resume

Press **Ctrl+C** anytime:

```
⚠️  Interrupt received. Finishing current operation...

❓ Do you want to finish and save? (Y/n): Y

✅ Progress saved!
📁 Output file: Austin_TX_0_245.csv
📊 Processed: 245 users
📍 Stopped at index: 245
```

Run again to resume from index 245!

## 🔌 Network Resilience

Handles network issues automatically:

```
🔌 Network disconnected. Waiting for connection...
   Checking again in 30 seconds...
✅ Network restored!
🔄 Resuming...
```

## 💾 Supabase Integration

### Benefits

- Real-time state sync
- Cross-machine progress
- Centralized management
- State history

### Setup

```bash
# 1. Create Supabase project
# 2. Run setup script
python setup_supabase.py

# 3. Select option 1 to insert regions
# 4. Set environment variables
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"

# 5. Run scraper (auto-syncs)
python gscraper.py
```

## 🧪 Testing

```bash
# Test setup
python test_setup.py

# Test features
python test_features.py

# Test regions
python test_regions.py
```

## 📊 Monitoring Progress

```bash
# Check local state
cat state.json

# Check Supabase state
python setup_supabase.py
# Select option 3: List states

# Watch in real-time
watch -n 5 cat state.json
```

## 🐛 Troubleshooting

| Issue            | Solution               |
| ---------------- | ---------------------- |
| Rate limit       | Set `GITHUB_TOKEN`     |
| Network error    | GScraper auto-retries  |
| Supabase error   | Check credentials      |
| No results       | Verify region ID       |
| Module not found | `pip install supabase` |

See `SETUP_GUIDE.md` for more help.

## 📖 Learn More

- **Setup**: Read `SETUP_GUIDE.md`
- **Agent mode**: Read `GSCRAPER_README.md`
- **CLI mode**: Read `USAGE_EXAMPLES.md`
- **Overview**: Read `PROJECT_SUMMARY.md`
- **Changes**: Read `CHANGELOG.md`

## 🎯 Use Cases

1. **Lead generation** - Find developers with verified contacts
2. **Recruitment** - Identify experienced developers
3. **Market research** - Analyze developer distribution
4. **Community building** - Find developers for communities
5. **Data analysis** - Study GitHub/Telegram correlations

## ⚡ Best Practices

1. ✅ Start with small limits (20 users)
2. ✅ Use GitHub token (avoid rate limits)
3. ✅ Enable Supabase (track progress)
4. ✅ Use delays ≥1 second (be respectful)
5. ✅ Monitor progress regularly
6. ✅ Backup CSV files
7. ✅ Verify data quality

## 🚧 Roadmap

- [ ] International regions
- [ ] More social platforms
- [ ] Web dashboard
- [ ] Email notifications
- [ ] Parallel scraping
- [ ] Advanced filtering

## 📄 License

MIT License

## 🤝 Contributing

Contributions welcome! Add regions, companies, or features.

## 📞 Support

- Check documentation files
- Run `python test_setup.py`
- Review examples in docs

## ⭐ Quick Commands

```bash
# Test everything
python test_setup.py

# Run agent (recommended)
python gscraper.py

# Run CLI
python github_scraper.py list
python github_scraper.py region 1

# Setup Supabase
python setup_supabase.py

# Check state
cat state.json
```

---

**Ready to scrape?** Run `python gscraper.py` and follow the prompts! 🚀
