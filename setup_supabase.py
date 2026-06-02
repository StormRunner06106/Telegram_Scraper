#!/usr/bin/env python3
"""Setup Supabase tables and insert region data.

Note: This script only manages the Regions table.
The States table already exists in your Supabase project and will be used as-is.
"""

import os
import sys
import json
from pathlib import Path

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        os.environ[key] = value

load_env()

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py not installed.")
    print("Install it with: pip install supabase")
    sys.exit(1)


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
PROJECT_ROOT = Path(__file__).resolve().parent
REGIONS_FILE = PROJECT_ROOT / "config" / "regions.json"
STATE_FILE = PROJECT_ROOT / "data" / "state" / "state.json"


def get_supabase_client() -> Client:
    """Get Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase not configured.")
        print("Set environment variables:")
        print("  export SUPABASE_URL='your-project-url'")
        print("  export SUPABASE_KEY='your-anon-key'")
        sys.exit(1)
    
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)


def create_tables_sql() -> str:
    """Return SQL to create tables."""
    return """
-- Regions table
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_regions_name ON regions(name);

-- Note: States table already exists in your Supabase project
-- The scraper will use the existing states table
"""


def load_regions_from_file() -> list[dict]:
    """Load regions from the config directory."""
    if not REGIONS_FILE.exists():
        print(f"❌ {REGIONS_FILE} not found")
        sys.exit(1)
    
    with REGIONS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def insert_regions(supabase: Client, regions: list[dict]) -> None:
    """Insert or update regions in Supabase."""
    print("\n📍 Inserting regions...")
    
    for region in regions:
        try:
            data = {
                "id": region["id"],
                "name": region["name"],
                "city": region["city"],
                "state": region["state"],
            }
            
            # Upsert (insert or update)
            result = supabase.table("regions").upsert(data, on_conflict="id").execute()
            print(f"  ✓ Region {region['id']}: {region['name']}")
        except Exception as e:
            print(f"  ❌ Failed to insert region {region['id']}: {e}")


def show_tables_info(supabase: Client) -> None:
    """Show information about tables."""
    print("\n📊 Database Status:")
    print("-" * 60)
    
    try:
        # Count regions
        result = supabase.table("regions").select("id", count="exact").execute()
        region_count = result.count if hasattr(result, 'count') else len(result.data)
        print(f"Regions: {region_count}")
        
        # Count states (using existing table)
        try:
            result = supabase.table("states").select("region_id", count="exact").execute()
            state_count = result.count if hasattr(result, 'count') else len(result.data)
            print(f"States: {state_count} (using existing table)")
        except Exception:
            print(f"States: Unable to access (table may not exist yet)")
        
    except Exception as e:
        print(f"⚠️  Could not fetch table info: {e}")


def list_regions(supabase: Client) -> None:
    """List all regions from Supabase."""
    print("\n📍 Regions in Supabase:")
    print("-" * 60)
    print(f"{'ID':<5} {'Name':<30} {'State':<20}")
    print("-" * 60)
    
    try:
        result = supabase.table("regions").select("*").order("id").execute()
        
        for region in result.data:
            region_id = region.get("id", "?")
            name = region.get("name", "Unknown")
            state = region.get("state", "Unknown")
            print(f"{region_id:<5} {name:<30} {state:<20}")
        
        print("-" * 60)
        print(f"Total: {len(result.data)} regions")
        
    except Exception as e:
        print(f"❌ Failed to list regions: {e}")


def list_states(supabase: Client) -> None:
    """List all states from Supabase."""
    print("\n📊 States in Supabase:")
    print("-" * 60)
    print(f"{'Region ID':<12} {'Index':<10} {'Processed':<12} {'Status':<12}")
    print("-" * 60)
    
    try:
        result = supabase.table("states").select("*").order("region_id").execute()
        
        if not result.data:
            print("No states found.")
        else:
            for state in result.data:
                region_id = state.get("region_id", "?")
                index = state.get("index", 0)
                total = state.get("total_processed", 0)
                status = "completed" if state.get("is_end", False) else "in progress"
                print(f"{region_id:<12} {index:<10} {total:<12} {status:<12}")
        
        print("-" * 60)
        print(f"Total: {len(result.data)} states")
        
    except Exception as e:
        print(f"❌ Failed to list states: {e}")


def reset_states(supabase: Client) -> None:
    """Reset all states."""
    confirm = input("\n⚠️  This will delete all state data. Continue? (yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("❌ Cancelled.")
        return
    
    try:
        result = supabase.table("states").delete().neq("region_id", -1).execute()
        print("✅ All states deleted.")
    except Exception as e:
        print(f"❌ Failed to reset states: {e}")


def load_states_from_file() -> list[dict]:
    """Load states from the data directory."""
    if not STATE_FILE.exists():
        print(f"❌ {STATE_FILE} not found")
        return []
    
    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def sync_states_to_supabase(supabase: Client) -> None:
    """Sync local scraper state to Supabase."""
    print(f"\n📤 Syncing states from {STATE_FILE} to Supabase...")
    
    states = load_states_from_file()
    
    if not states:
        print(f"⚠️  No states found in {STATE_FILE}")
        return
    
    print(f"Found {len(states)} states in {STATE_FILE}")
    
    synced = 0
    failed = 0
    
    for state in states:
        try:
            region_id = state.get("region_id")
            data = {
                "region_id": region_id,
                "index": state.get("index", 0),
                "is_end": state.get("is_end", False),
                "total_processed": state.get("total_processed", 0),
            }
            
            # Check if record exists
            existing = supabase.table("states").select("*").eq("region_id", region_id).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing record
                result = supabase.table("states").update(data).eq("region_id", region_id).execute()
                print(f"  ✓ Updated region {region_id}: index={data['index']}, processed={data['total_processed']}")
            else:
                # Insert new record
                result = supabase.table("states").insert(data).execute()
                print(f"  ✓ Inserted region {region_id}: index={data['index']}, processed={data['total_processed']}")
            
            synced += 1
        except Exception as e:
            print(f"  ❌ Failed to sync region {state.get('region_id')}: {e}")
            failed += 1
    
    print(f"\n✅ Synced {synced} states to Supabase")
    if failed > 0:
        print(f"⚠️  Failed to sync {failed} states")



def main():
    """Main entry point."""
    print("=" * 60)
    print("  🗄️  Supabase Setup for GitHub Scraper")
    print("=" * 60)
    print("\n⚠️  Note: States table already exists in your Supabase.")
    print("This script only manages the Regions table.\n")
    
    # Get Supabase client
    supabase = get_supabase_client()
    print("✅ Connected to Supabase")
    
    # Show menu
    while True:
        print("\n📋 Menu:")
        print(f"  1. Insert/Update regions from {REGIONS_FILE}")
        print("  2. List regions")
        print("  3. List states (from existing table)")
        print(f"  4. Sync states from {STATE_FILE} to Supabase")
        print("  5. Reset all states (from existing table)")
        print("  6. Show database status")
        print("  7. Show SQL for manual regions table creation")
        print("  0. Exit")
        
        choice = input("\n👉 Select option: ").strip()
        
        if choice == "1":
            regions = load_regions_from_file()
            insert_regions(supabase, regions)
            print(f"\n✅ Inserted {len(regions)} regions")
        
        elif choice == "2":
            list_regions(supabase)
        
        elif choice == "3":
            list_states(supabase)
        
        elif choice == "4":
            sync_states_to_supabase(supabase)
        
        elif choice == "5":
            reset_states(supabase)
        
        elif choice == "6":
            show_tables_info(supabase)
        
        elif choice == "7":
            print("\n📝 SQL for regions table creation:")
            print("-" * 60)
            print(create_tables_sql())
            print("-" * 60)
            print("\nRun this SQL in your Supabase SQL Editor to create the regions table.")
            print("(States table already exists and will be used as-is)")
        
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option. Try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
