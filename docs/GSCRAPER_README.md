# GScraper - GitHub Scraper Agent

Interactive, network-resilient GitHub scraper with automatic resume and Supabase sync.

## Features

- 🔄 **Auto-resume**: Automatically resumes from where it left off
- 🔌 **Network resilience**: Waits for network and retries automatically
- 💾 **Supabase sync**: Real-time state synchronization (optional)
- 🎯 **Interactive CLI**: Step-by-step guided setup
- 📊 **Progress tracking**: Detailed progress with index ranges
- 🛑 **Graceful shutdown**: Ctrl+C to pause and save progress
- 📁 **Smart file naming**: Files named with index ranges

## Quick Start

### 1. Install Dependencies (Optional)

For Supabase sync:

```bash
pip install supabase
```

### 2. Run GScraper

```bash
python gscraper.py
```

### 3. Follow Interactive Prompts

The CLI will guide you through:

1. **Select region** - Choose from 20 predefined regions
2. **Input limit** - How many users to fetch (max 1000)
3. **Output filename** - Default: `{region}_{start_index}.csv`

### 4. Let It Run

The scraper will:

- Fetch GitHub users from the selected region
- Check account age, badges, and Telegram accounts
- Save progress every 10 users
- Auto-resume if network drops
- Rename file with index range when done

## Usage Examples

### Basic Usage (No Supabase)

```bash
python gscraper.py
```

Select region → Input limit → Input filename → Start scraping

### With Supabase Sync

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
python gscraper.py
```

### Pause and Resume

Press **Ctrl+C** during scraping:

```
⚠️  Interrupt received. Finishing current operation...

❓ Do you want to finish and save? (Y/n): Y

✅ Progress saved!
📁 Output file: Austin_TX_0_245.csv
📊 Processed: 245 users
📍 Stopped at index: 245
```

Run again to resume:

```bash
python gscraper.py
# Select same region → It will resume from index 245
```

## File Naming

Files are automatically renamed with index ranges:

**During scraping:**

```
Austin_TX_0.csv
```

**After completion/pause:**

```
Austin_TX_0_500.csv  # Scraped users 0-500
```

This helps you track which data is in each file.

## Supabase Setup

### 1. Create Tables

Run the setup script:

```bash
python setup_supabase.py
```

Or manually create the regions table in Supabase SQL Editor:

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

CREATE INDEX IF NOT EXISTS idx_regions_name ON regions(name);
```

**Note**: The States table already exists in your Supabase project and will be used as-is.

### 2. Insert Regions

```bash
python setup_supabase.py
# Select option 1: Insert/Update regions
```

### 3. Configure Environment

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export GITHUB_TOKEN="your-github-token"  # Optional but recommended
```

### 4. Run GScraper

```bash
python gscraper.py
```

State will be synced to Supabase automatically!

## Setup Script Features

The `setup_supabase.py` script provides:

1. **Insert/Update regions** - Sync regions.json to Supabase
2. **List regions** - View all regions in database
3. **List states** - View scraping progress
4. **Reset states** - Clear all progress (fresh start)
5. **Show database status** - Table counts
6. **Show SQL** - Get SQL for manual table creation

## Network Resilience

GScraper handles network issues automatically:

```
🔌 Network disconnected. Waiting for connection...
   Checking again in 30 seconds...
   Checking again in 30 seconds...
✅ Network restored!
🔄 Iteration 2
```

No manual intervention needed!

## Configuration

### Environment Variables

```bash
# Required for Supabase sync
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"

# Optional but recommended
export GITHUB_TOKEN="your-github-token"
```

### Delay Between Requests

Default: 1 second (configurable in code)

```python
run_scraper_loop(
    region_id=region_id,
    max_results=limit,
    output_filename=output_filename,
    delay=1.0,  # Change this
    supabase=supabase,
)
```

## Troubleshooting

### "supabase-py not installed"

```bash
pip install supabase
```

### "Supabase not configured"

Set environment variables:

```bash
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"
```

### Network keeps disconnecting

GScraper will wait automatically. You can adjust check interval in code:

```python
wait_for_network(check_interval=30)  # Check every 30 seconds
```

### Want to start fresh

Option 1: Use setup script

```bash
python setup_supabase.py
# Select option 4: Reset all states
```

Option 2: Delete local state

```bash
rm state.json
```

## Comparison: gscraper.py vs github_scraper.py

| Feature            | gscraper.py       | github_scraper.py |
| ------------------ | ----------------- | ----------------- |
| Interactive CLI    | ✅ Yes            | ❌ No             |
| Network resilience | ✅ Auto-retry     | ❌ Manual         |
| Supabase sync      | ✅ Yes            | ❌ No             |
| File naming        | ✅ Index ranges   | ❌ Static         |
| Graceful shutdown  | ✅ Ctrl+C handler | ❌ Basic          |
| Progress tracking  | ✅ Real-time      | ✅ Yes            |
| Resume capability  | ✅ Automatic      | ✅ Manual         |

**Use gscraper.py for**: Long-running, unattended scraping with auto-recovery

**Use github_scraper.py for**: Quick one-off scrapes or scripting

## Advanced Usage

### Run Multiple Regions

Create a bash script:

```bash
#!/bin/bash
# scrape_all.sh

export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"
export GITHUB_TOKEN="your-token"

# Scrape regions 1-5
for region_id in {1..5}; do
    echo "Starting region $region_id"
    python gscraper.py <<EOF
$region_id
Y
1000
Y

Y
EOF
done
```

### Monitor Progress

```bash
# Watch state file
watch -n 5 cat state.json

# Or query Supabase
python setup_supabase.py
# Select option 3: List states
```

## Tips

1. **Start small**: Test with limit=20 first
2. **Use GitHub token**: Avoid rate limits
3. **Enable Supabase**: Track progress across machines
4. **Monitor network**: GScraper handles it, but good to know
5. **Check output files**: Verify data quality periodically
6. **Backup state.json**: Keep a copy before major changes

## License

Same as parent project.
