#!/usr/bin/env python3
"""Test setup and verify all components are working."""

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def test_python_version():
    """Test Python version."""
    print("🐍 Testing Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (need 3.10+)")
        return False


def test_files_exist():
    """Test required files exist."""
    print("\n📁 Testing required files...")
    
    required_files = [
        "github_scraper.py",
        "gscraper.py",
        "setup_supabase.py",
        "config/regions.json",
        "requirements.txt",
    ]
    
    all_exist = True
    for filename in required_files:
        if (PROJECT_ROOT / filename).exists():
            print(f"   ✅ {filename}")
        else:
            print(f"   ❌ {filename} (missing)")
            all_exist = False
    
    return all_exist


def test_regions_json():
    """Test regions.json is valid."""
    print("\n📍 Testing regions.json...")
    
    try:
        import json
        with (CONFIG_DIR / "regions.json").open("r", encoding="utf-8") as f:
            regions = json.load(f)
        
        if not regions:
            print("   ❌ No regions found")
            return False
        
        print(f"   ✅ {len(regions)} regions loaded")
        
        # Test first region structure
        first = regions[0]
        required_keys = ["id", "name", "city", "state"]
        for key in required_keys:
            if key not in first:
                print(f"   ❌ Missing key: {key}")
                return False
        
        print(f"   ✅ Region structure valid")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_imports():
    """Test required imports."""
    print("\n📦 Testing imports...")
    
    # Test standard library
    try:
        import json
        import csv
        import urllib.request
        print("   ✅ Standard library")
    except ImportError as e:
        print(f"   ❌ Standard library: {e}")
        return False
    
    # Test github_scraper imports
    try:
        from github_scraper import load_regions, get_region_by_id
        print("   ✅ github_scraper module")
    except ImportError as e:
        print(f"   ❌ github_scraper module: {e}")
        return False
    
    # Test supabase (optional)
    try:
        from supabase import create_client
        print("   ✅ supabase (optional)")
    except ImportError:
        print("   ⚠️  supabase not installed (optional)")
    
    return True


def test_environment():
    """Test environment variables."""
    print("\n🔧 Testing environment variables...")
    
    github_token = os.getenv("GITHUB_TOKEN")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if github_token:
        print(f"   ✅ GITHUB_TOKEN set ({len(github_token)} chars)")
    else:
        print("   ⚠️  GITHUB_TOKEN not set (recommended)")
    
    if supabase_url:
        print(f"   ✅ SUPABASE_URL set")
    else:
        print("   ⚠️  SUPABASE_URL not set (optional)")
    
    if supabase_key:
        print(f"   ✅ SUPABASE_KEY set ({len(supabase_key)} chars)")
    else:
        print("   ⚠️  SUPABASE_KEY not set (optional)")
    
    return True


def test_network():
    """Test network connectivity."""
    print("\n🌐 Testing network connectivity...")
    
    try:
        import urllib.request
        urllib.request.urlopen("https://api.github.com", timeout=5)
        print("   ✅ GitHub API reachable")
        return True
    except Exception as e:
        print(f"   ❌ Network error: {e}")
        return False


def test_github_scraper():
    """Test github_scraper functions."""
    print("\n🔍 Testing github_scraper functions...")
    
    try:
        from github_scraper import load_regions, get_region_by_id, get_region_state
        
        # Test load_regions
        regions = load_regions()
        if not regions:
            print("   ❌ load_regions() returned empty")
            return False
        print(f"   ✅ load_regions() → {len(regions)} regions")
        
        # Test get_region_by_id
        region = get_region_by_id(1)
        if not region:
            print("   ❌ get_region_by_id(1) returned None")
            return False
        print(f"   ✅ get_region_by_id(1) → {region['name']}")
        
        # Test get_region_state
        state = get_region_state(1)
        print(f"   ✅ get_region_state(1) → index={state.index}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("  🧪 GitHub Scraper Setup Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Python version", test_python_version()))
    results.append(("Required files", test_files_exist()))
    results.append(("regions.json", test_regions_json()))
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_environment()))
    results.append(("Network", test_network()))
    results.append(("github_scraper", test_github_scraper()))
    
    print("\n" + "=" * 60)
    print("  📊 Test Results")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! You're ready to scrape!")
        print("\nNext steps:")
        print("  1. Run: python gscraper.py")
        print("  2. Or: python github_scraper.py list")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues above.")
        print("\nCheck:")
        print("  - SETUP_GUIDE.md for setup instructions")
        print("  - README.md for general documentation")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")
        sys.exit(130)
