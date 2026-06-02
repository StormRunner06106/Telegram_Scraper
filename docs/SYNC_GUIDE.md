# State Sync Guide

## Overview

The scraper maintains progress in two places:

1. **Local**: `state.json` file
2. **Remote**: Supabase `states` table

## Automatic Sync

When using `gscraper.py`, states are automatically synced:

- ✅ Loaded from Supabase on startup
- ✅ Saved to local `state.json` every 10 users
- ✅ Synced to Supabase after each scraping session

## Manual Sync

### Sync Local → Supabase

If you have progress in `state.json` that's not in Supabase:

```bash
python setup_supabase.py
# Select option 4: Sync states from state.json to Supabase
```

This will:

1. Read all states from `state.json`
2. Upsert each state to Supabase `states` table
3. Show progress for each region

### Example Output

```
📤 Syncing states from state.json to Supabase...
Found 3 states in state.json
  ✓ Synced region 1: index=245, processed=245
  ✓ Synced region 2: index=500, processed=500
  ✓ Synced region 3: index=1000, processed=1000

✅ Synced 3 states to Supabase
```

## When to Use Manual Sync

### Scenario 1: First Time Setup

You've been using the scraper locally and now want to enable Supabase:

```bash
# 1. Configure Supabase in .env
# 2. Setup regions table
python setup_supabase.py
# Option 1: Insert regions

# 3. Sync existing progress
python setup_supabase.py
# Option 4: Sync states
```

### Scenario 2: Restore from Backup

You have a backup `state.json` and want to restore it:

```bash
# 1. Copy backup to state.json
cp state.backup.json state.json

# 2. Sync to Supabase
python setup_supabase.py
# Option 4: Sync states
```

### Scenario 3: Multiple Machines

You've been scraping on machine A and want to continue on machine B:

**On Machine A:**

```bash
# Progress is already in Supabase (automatic)
# Or manually sync:
python setup_supabase.py
# Option 4: Sync states
```

**On Machine B:**

```bash
# Just run the scraper - it will load from Supabase
python gscraper.py
```

## State File Format

### state.json

```json
[
  {
    "region_id": 1,
    "index": 245,
    "is_end": false,
    "total_processed": 245
  },
  {
    "region_id": 2,
    "index": 500,
    "is_end": true,
    "total_processed": 500
  }
]
```

### Supabase states Table

```
region_id | index | is_end | total_processed | updated_at
----------|-------|--------|-----------------|------------
1         | 245   | false  | 245             | 2026-05-07 10:30:00
2         | 500   | true   | 500             | 2026-05-07 11:45:00
```

## Sync Direction

### Local → Supabase (Manual)

```bash
python setup_supabase.py
# Option 4: Sync states from state.json to Supabase
```

### Supabase → Local (Automatic)

```bash
python gscraper.py
# Automatically loads from Supabase on startup
```

## Conflict Resolution

When syncing, the **local state.json takes precedence**:

- Upsert operation updates Supabase with local values
- Existing Supabase data is overwritten
- No merge - local state wins

## Verification

### Check Local State

```bash
cat state.json
```

### Check Supabase State

```bash
python setup_supabase.py
# Option 3: List states
```

### Compare

```bash
# Local
cat state.json

# Remote
python setup_supabase.py
# Option 3: List states

# Should match after sync
```

## Troubleshooting

### "state.json not found"

Create it or run the scraper first:

```bash
python gscraper.py
# This will create state.json
```

### "Failed to sync region X"

Check:

1. Supabase connection: `python check_env.py`
2. States table exists in Supabase
3. Region ID is valid

### States don't match

Sync local to Supabase:

```bash
python setup_supabase.py
# Option 4: Sync states
```

## Best Practices

1. **Enable Supabase from start**: Configure before first scrape
2. **Let automatic sync work**: Don't manually sync unless needed
3. **Backup state.json**: Keep copies before major changes
4. **Verify after sync**: Check both local and remote states
5. **Use one source of truth**: Either local or Supabase, not both

## Commands Summary

```bash
# Check local state
cat state.json

# Check remote state
python setup_supabase.py
# Option 3: List states

# Sync local → remote
python setup_supabase.py
# Option 4: Sync states

# Reset all states
python setup_supabase.py
# Option 5: Reset all states

# Run scraper (auto-sync)
python gscraper.py
```

## Example Workflow

### Initial Setup

```bash
# 1. Configure environment
python check_env.py

# 2. Setup Supabase
python setup_supabase.py
# Option 1: Insert regions

# 3. Run scraper (creates state.json)
python gscraper.py
# States automatically synced to Supabase
```

### Resume on Another Machine

```bash
# 1. Configure environment
python check_env.py

# 2. Run scraper
python gscraper.py
# Automatically loads state from Supabase
```

### Backup and Restore

```bash
# Backup
cp state.json state.backup.json

# Restore
cp state.backup.json state.json

# Sync to Supabase
python setup_supabase.py
# Option 4: Sync states
```

## FAQ

**Q: Do I need to manually sync?**
A: No, if you're using `gscraper.py` with Supabase configured, it syncs automatically.

**Q: What if I forget to sync?**
A: Run the scraper again - it will load from Supabase and continue.

**Q: Can I edit state.json manually?**
A: Yes, then sync to Supabase with option 4.

**Q: What happens if I sync empty state.json?**
A: Nothing - it will show "No states found in state.json".

**Q: Can I sync from Supabase to local?**
A: The scraper does this automatically on startup.

---

**Need help?** Check `READY_TO_USE.md` for complete setup guide.
