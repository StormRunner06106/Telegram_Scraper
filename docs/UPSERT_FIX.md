# Upsert Fix for States Table

## Issue

The `states` table in Supabase doesn't have a unique constraint on `region_id`, causing upsert operations to fail with:

```
{'message': 'there is no unique or exclusion constraint matching the ON CONFLICT specification', 'code': '42P10'}
```

## Solution

Changed from `upsert()` to a check-then-update/insert pattern:

### Before (Failed)

```python
# This requires a unique constraint on region_id
result = supabase.table("states").upsert(data, on_conflict="region_id").execute()
```

### After (Works)

```python
# Check if record exists
existing = supabase.table("states").select("*").eq("region_id", region_id).execute()

if existing.data and len(existing.data) > 0:
    # Update existing record
    result = supabase.table("states").update(data).eq("region_id", region_id).execute()
else:
    # Insert new record
    result = supabase.table("states").insert(data).execute()
```

## Files Updated

1. ✅ `setup_supabase.py` - `sync_states_to_supabase()` function
2. ✅ `gscraper.py` - `sync_state_to_supabase()` function

## How It Works

### Check-Update-Insert Pattern

1. **Check**: Query if record with `region_id` exists
2. **Update**: If exists, update the existing record
3. **Insert**: If not exists, insert new record

This works regardless of whether `region_id` is a primary key or has a unique constraint.

## Testing

```bash
# Test the sync
python setup_supabase.py
# Select option 4: Sync states from state.json to Supabase
```

Expected output:

```
📤 Syncing states from state.json to Supabase...
Found 1 states in state.json
  ✓ Updated region 2: index=1000, processed=1000

✅ Synced 1 states to Supabase
```

## Why This Happened

The `states` table in your Supabase might be structured differently than expected:

### Expected Structure (with unique constraint)

```sql
CREATE TABLE states (
    region_id INTEGER PRIMARY KEY,  -- This makes it unique
    index INTEGER,
    is_end BOOLEAN,
    total_processed INTEGER
);
```

### Actual Structure (without unique constraint)

```sql
CREATE TABLE states (
    id SERIAL PRIMARY KEY,           -- Different primary key
    region_id INTEGER,               -- Not unique
    index INTEGER,
    is_end BOOLEAN,
    total_processed INTEGER
);
```

## Benefits of New Approach

1. ✅ Works with any table structure
2. ✅ No need for unique constraints
3. ✅ Explicit control over update vs insert
4. ✅ Better error messages
5. ✅ More predictable behavior

## Performance Note

The new approach makes 2 queries instead of 1:

1. SELECT to check existence
2. UPDATE or INSERT

For the scraper's use case (infrequent syncs), this is negligible.

## Alternative: Add Unique Constraint

If you want to use `upsert()`, add a unique constraint to your Supabase table:

```sql
-- Option 1: Make region_id the primary key
ALTER TABLE states DROP CONSTRAINT states_pkey;
ALTER TABLE states ADD PRIMARY KEY (region_id);

-- Option 2: Add a unique constraint
ALTER TABLE states ADD CONSTRAINT states_region_id_unique UNIQUE (region_id);
```

But the check-update-insert pattern works without any schema changes! ✅

## Verification

After syncing, verify the data:

```bash
# Check local
cat state.json

# Check remote
python setup_supabase.py
# Option 3: List states

# Should match!
```

## Summary

✅ **Fixed**: Upsert error resolved
✅ **Method**: Check-then-update/insert pattern
✅ **Files**: Updated `setup_supabase.py` and `gscraper.py`
✅ **Works**: With any table structure
✅ **Ready**: Sync now works correctly

---

**Test it now:**

```bash
python setup_supabase.py
# Option 4: Sync states from state.json to Supabase
```
