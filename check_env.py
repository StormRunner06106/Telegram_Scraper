#!/usr/bin/env python3
"""Check environment variables and .env file."""

import os
import sys
from pathlib import Path


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


def mask_value(value: str, show_chars: int = 10) -> str:
    """Mask sensitive values."""
    if not value:
        return "(not set)"
    if len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "..." + "*" * (len(value) - show_chars)


def main():
    """Check environment variables."""
    print("=" * 60)
    print("  🔧 Environment Variables Check")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("\n✅ .env file found")
        load_env()
    else:
        print("\n⚠️  .env file not found")
        print("   Create it from .env.example:")
        print("   cp .env.example .env")
    
    print("\n📋 Current Configuration:")
    print("-" * 60)
    
    # Check GitHub token
    github_token = os.getenv("GITHUB_TOKEN", "")
    if github_token:
        print(f"✅ GITHUB_TOKEN: {mask_value(github_token, 15)}")
    else:
        print("❌ GITHUB_TOKEN: (not set)")
        print("   Get token from: https://github.com/settings/tokens")
    
    # Check Supabase URL
    supabase_url = os.getenv("SUPABASE_URL", "")
    if supabase_url and supabase_url != "https://your-project-id.supabase.co":
        print(f"✅ SUPABASE_URL: {supabase_url}")
    elif supabase_url:
        print(f"⚠️  SUPABASE_URL: {supabase_url}")
        print("   Replace with your actual Supabase project URL")
    else:
        print("❌ SUPABASE_URL: (not set)")
        print("   Get from: Supabase Dashboard → Project Settings → API")
    
    # Check Supabase key
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if supabase_key and supabase_key != "your_supabase_anon_key_here":
        print(f"✅ SUPABASE_KEY: {mask_value(supabase_key, 20)}")
    elif supabase_key:
        print(f"⚠️  SUPABASE_KEY: {supabase_key}")
        print("   Replace with your actual Supabase anon key")
    else:
        print("❌ SUPABASE_KEY: (not set)")
        print("   Get from: Supabase Dashboard → Project Settings → API")
    
    print("-" * 60)
    
    # Summary
    print("\n📊 Summary:")
    
    all_set = (
        github_token and 
        supabase_url and supabase_url != "https://your-project-id.supabase.co" and
        supabase_key and supabase_key != "your_supabase_anon_key_here"
    )
    
    if all_set:
        print("✅ All environment variables are configured!")
        print("\nNext steps:")
        print("  1. Run: python setup_supabase.py")
        print("  2. Run: python gscraper.py")
    else:
        print("⚠️  Some environment variables need configuration")
        print("\nNext steps:")
        print("  1. Edit .env file with your credentials")
        print("  2. Run: python check_env.py (to verify)")
        print("  3. Run: python setup_supabase.py")
        print("  4. Run: python gscraper.py")
    
    print("\n💡 Tips:")
    print("  - GitHub token: Required for higher API limits")
    print("  - Supabase: Optional but recommended for state sync")
    print("  - .env file is in .gitignore (safe from commits)")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")
        sys.exit(0)
