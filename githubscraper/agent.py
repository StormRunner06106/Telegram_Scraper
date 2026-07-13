#!/usr/bin/env python3
"""GitHub Scraper Agent - Interactive CLI with network resilience and Supabase sync."""

from __future__ import annotations

import os
import sys
import time
import signal
from pathlib import Path
from typing import Any

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

# Import scraper functions
from githubscraper.core import (
    DEFAULT_CONTACTS_FILE,
    LOGGER,
    REGIONS_FILE,
    load_regions,
    get_region_by_id,
    get_region_state,
    log_environment_status,
    setup_logging,
    update_region_state,
    scrape_region,
)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: supabase-py not installed. Run: pip install supabase")


# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    shutdown_requested = True
    print("\n\n⚠️  Interrupt received. Finishing current operation...")


def get_supabase_client() -> Client | None:
    """Get Supabase client if configured."""
    if not SUPABASE_AVAILABLE:
        return None
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        return None
    
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️  Failed to connect to Supabase: {e}")
        LOGGER.exception("Failed to connect to Supabase")
        return None


def sync_state_to_supabase(supabase: Client | None, region_id: int, index: int, is_end: bool, total_processed: int) -> bool:
    """Sync state to Supabase."""
    if not supabase:
        return False
    
    try:
        data = {
            "region_id": region_id,
            "index": index,
            "is_end": is_end,
            "total_processed": total_processed,
        }
        
        # Check if record exists
        existing = supabase.table("states").select("*").eq("region_id", region_id).execute()
        
        if existing.data and len(existing.data) > 0:
            # Update existing record
            result = supabase.table("states").update(data).eq("region_id", region_id).execute()
        else:
            # Insert new record
            result = supabase.table("states").insert(data).execute()
        
        return True
    except Exception as e:
        print(f"⚠️  Failed to sync to Supabase: {e}")
        LOGGER.exception("Failed to sync state to Supabase region_id=%s", region_id)
        return False


def load_state_from_supabase(supabase: Client | None, region_id: int) -> dict[str, Any] | None:
    """Load state from Supabase."""
    if not supabase:
        return None
    
    try:
        result = supabase.table("states").select("*").eq("region_id", region_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"⚠️  Failed to load from Supabase: {e}")
        LOGGER.exception("Failed to load state from Supabase region_id=%s", region_id)
        return None


def check_network() -> bool:
    """Check if network is available."""
    import urllib.request
    try:
        urllib.request.urlopen("https://api.github.com", timeout=5)
        return True
    except:
        return False


def wait_for_network(check_interval: int = 30) -> None:
    """Wait until network is available."""
    print("\n🔌 Network disconnected. Waiting for connection...")
    while not check_network():
        print(f"   Checking again in {check_interval} seconds...")
        time.sleep(check_interval)
    print("✅ Network restored!")


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_banner():
    """Show application banner."""
    print("=" * 60)
    print("  🔍 GitHub Scraper Agent")
    print("  Network-resilient scraping with auto-resume")
    print("=" * 60)
    print()


def select_region() -> int | None:
    """Interactive region selection."""
    regions = load_regions()
    if not regions:
        print(f"❌ No regions found in {REGIONS_FILE}")
        return None
    
    print("\n📍 Available Regions:")
    print("-" * 60)
    print(f"{'ID':<5} {'Name':<30} {'State':<20}")
    print("-" * 60)
    
    for region in regions:
        region_id = region.get("id", "?")
        name = region.get("name", "Unknown")
        state_name = region.get("state", "Unknown")
        print(f"{region_id:<5} {name:<30} {state_name:<20}")
    
    print("-" * 60)
    
    while True:
        try:
            region_input = input("\n👉 Enter region ID (or 'q' to quit): ").strip()
            if region_input.lower() == 'q':
                return None
            
            region_id = int(region_input)
            region = get_region_by_id(region_id)
            
            if not region:
                print(f"❌ Region ID {region_id} not found. Try again.")
                continue
            
            print(f"\n✓ Selected: {region['name']}")
            confirm = input("   Continue? (Y/n): ").strip().lower()
            
            if confirm in ['', 'y', 'yes']:
                return region_id
            
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n")
            return None


def input_limit() -> int | None:
    """Input data limit."""
    print("\n📊 Data Limit")
    print("-" * 60)
    print("How many GitHub users should be checked (profile, badges, Telegram)?")
    print("(Default: 1000. Use a very large number to process as many search results as possible.)")
    print("Note: this is not how many contacts will be saved; most users are filtered out.")
    
    while True:
        try:
            limit_input = input("\n👉 Enter limit (or press Enter for 1000): ").strip()
            
            if not limit_input:
                limit = 1000
            else:
                limit = int(limit_input)
            
            if limit < 1:
                print("❌ Limit must be at least 1.")
                continue
            
            print(f"\n✓ Limit set to: {limit}")
            confirm = input("   Continue? (Y/n): ").strip().lower()
            
            if confirm in ['', 'y', 'yes']:
                return limit
            
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n")
            return None


def input_output_filename(region_id: int, start_index: int) -> str | None:
    """Input output filename."""
    region = get_region_by_id(region_id)
    region_name = region.get("name", f"region{region_id}").replace(", ", "_").replace(" ", "_")
    default_filename = str(DEFAULT_CONTACTS_FILE.parent / f"{region_name}_{start_index}.csv")
    
    print("\n💾 Output Filename")
    print("-" * 60)
    print(f"Default: {default_filename}")
    print("(Will be renamed to include end index when finished)")
    
    while True:
        try:
            filename_input = input(f"\n👉 Enter filename (or press Enter for default): ").strip()
            
            if not filename_input:
                filename = default_filename
            else:
                filename = filename_input
                if not filename.endswith('.csv'):
                    filename += '.csv'
            
            print(f"\n✓ Output file: {filename}")
            confirm = input("   Continue? (Y/n): ").strip().lower()
            
            if confirm in ['', 'y', 'yes']:
                return filename
            
        except KeyboardInterrupt:
            print("\n")
            return None


def rename_output_file(original_filename: str, region_id: int, start_index: int, end_index: int) -> str:
    """Rename output file to include index range."""
    region = get_region_by_id(region_id)
    region_name = region.get("name", f"region{region_id}").replace(", ", "_").replace(" ", "_")
    
    # Remove .csv extension
    base = original_filename.replace('.csv', '')
    
    # Create new filename with range
    original_path = Path(original_filename)
    new_filename = str(original_path.parent / f"{region_name}_{start_index}_{end_index}.csv")
    
    # Rename if file exists
    if original_path.exists():
        try:
            original_path.rename(new_filename)
            print(f"✓ Renamed: {original_filename} → {new_filename}")
        except Exception as e:
            print(f"⚠️  Could not rename file: {e}")
            LOGGER.exception("Could not rename output file source=%s target=%s", original_filename, new_filename)
            return original_filename
    
    return new_filename


def run_scraper_loop(
    region_id: int,
    max_results: int,
    output_filename: str,
    delay: float = 1.0,
    supabase: Client | None = None,
) -> None:
    """Run scraper in a resilient loop."""
    global shutdown_requested
    
    # Load initial state
    state = get_region_state(region_id)
    start_index = state.index
    
    print("\n" + "=" * 60)
    print("🚀 Starting scraper agent...")
    print("=" * 60)
    print(f"Region ID: {region_id}")
    print(f"Max results: {max_results}")
    print(f"Output file: {output_filename}")
    print(f"Starting from index: {start_index}")
    print(f"Delay: {delay}s")
    print("=" * 60)
    print("\n💡 Press Ctrl+C to pause and save progress\n")
    LOGGER.info(
        "Agent loop started region_id=%s max_results=%s output=%s start_index=%s delay=%s",
        region_id,
        max_results,
        output_filename,
        start_index,
        delay,
    )
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    iteration = 0
    
    while not shutdown_requested:
        iteration += 1
        print(f"\n🔄 Iteration {iteration}")
        LOGGER.info("Agent iteration started region_id=%s iteration=%s", region_id, iteration)
        
        # Check network
        if not check_network():
            wait_for_network()
        
        try:
            # Sync state from Supabase before starting
            if supabase:
                remote_state = load_state_from_supabase(supabase, region_id)
                if remote_state:
                    print(f"📥 Loaded state from Supabase: index={remote_state.get('index', 0)}")
            
            # Run scraper
            added = scrape_region(
                region_id=region_id,
                output_path=Path(output_filename),
                max_results=max_results,
                delay_seconds=delay,
                token=os.getenv("GITHUB_TOKEN"),
                resume=True,
            )
            
            # Sync state to Supabase after scraping
            if supabase:
                state = get_region_state(region_id)
                sync_state_to_supabase(supabase, region_id, state.index, state.is_end, state.total_processed)
            
            # Check if completed
            state = get_region_state(region_id)
            if state.is_end:
                print("\n✅ Scraping completed!")
                final_filename = rename_output_file(output_filename, region_id, start_index, state.index)
                print(f"📁 Final file: {final_filename}")
                break
            
        except KeyboardInterrupt:
            # Already handled by signal handler
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("⏳ Waiting 60 seconds before retry...")
            LOGGER.exception("Agent iteration failed region_id=%s iteration=%s", region_id, iteration)
            time.sleep(60)
    
    # Handle shutdown
    if shutdown_requested:
        print("\n" + "=" * 60)
        confirm = input("❓ Do you want to finish and save? (Y/n): ").strip().lower()
        
        if confirm in ['', 'y', 'yes']:
            state = get_region_state(region_id)
            final_filename = rename_output_file(output_filename, region_id, start_index, state.index)
            
            # Final sync to Supabase
            if supabase:
                sync_state_to_supabase(supabase, region_id, state.index, state.is_end, state.total_processed)
                print("📤 Synced final state to Supabase")
            
            print("\n✅ Progress saved!")
            print(f"📁 Output file: {final_filename}")
            print(f"📊 Processed: {state.total_processed} users")
            print(f"📍 Stopped at index: {state.index}")
        else:
            print("\n❌ Cancelled without saving.")


def main():
    """Main entry point."""
    log_path = setup_logging()
    LOGGER.info("Agent environment file status path=%s exists=%s", Path(".env").resolve(), Path(".env").exists())
    log_environment_status("gscraper_agent")
    LOGGER.info("Interactive agent started arguments=%s", sys.argv[1:])
    clear_screen()
    show_banner()
    print(f"Log file: {log_path.resolve()}")
    
    # Initialize Supabase
    supabase = get_supabase_client()
    if supabase:
        print("✅ Connected to Supabase")
    else:
        print("⚠️  Running without Supabase sync")
    
    print("\n")
    
    # Step 1: Select region
    region_id = select_region()
    if region_id is None:
        print("\n👋 Goodbye!")
        return 0
    
    # Step 2: Input limit
    limit = input_limit()
    if limit is None:
        print("\n👋 Goodbye!")
        return 0
    
    # Step 3: Input output filename
    state = get_region_state(region_id)
    output_filename = input_output_filename(region_id, state.index)
    if output_filename is None:
        print("\n👋 Goodbye!")
        return 0
    
    # Step 4: Run scraper loop
    try:
        run_scraper_loop(
            region_id=region_id,
            max_results=limit,
            output_filename=output_filename,
            delay=1.0,
            supabase=supabase,
        )
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        LOGGER.exception("Fatal interactive agent error")
        return 1
    
    print("\n👋 Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
