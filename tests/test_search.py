import urllib.request
import json
import os
import urllib.parse

if __name__ != "__main__":
    import pytest

    pytest.skip("live GitHub smoke script", allow_module_level=True)

token = os.getenv("GITHUB_TOKEN")
if not token:
    raise SystemExit("Set GITHUB_TOKEN to run this live GitHub API smoke test.")

# Test different search queries
queries = [
    'location:"Austin, Texas, United States"',
    'location:"Austin, Texas"',
    'location:"Austin, TX"',
    'location:Austin location:Texas',
    'location:Austin',
]

for query in queries:
    url = 'https://api.github.com/search/users?' + urllib.parse.urlencode({'q': query, 'per_page': 1})
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'User-Agent': 'GithubScraper/0.1'
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            print(f"{query:50} -> {data['total_count']:,} users")
    except Exception as e:
        print(f"{query:50} -> Error: {e}")
