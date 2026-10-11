"""
Inspect the existing interview_logs table structure via the Supabase REST API.
Also checks for any other existing tables related to interviews.
"""
import urllib.request
import json

SUPABASE_URL = "https://fotdyidbreamqmyhsyfg.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvdGR5aWRicmVhbXFteWhzeWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2MTAxMjMsImV4cCI6MjEwMjE4NjEyM30"
    ".XTxEL1ZJCpamm4VG9rXQKr0aw5TZJp-QHQ7IgwvoUpw"
)

HEADERS = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Accept": "application/json",
}


def fetch(path: str, label: str):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode()
            print(f"\n=== {label} (HTTP {r.status}) ===")
            try:
                parsed = json.loads(body)
                print(json.dumps(parsed, indent=2)[:1200])
            except Exception:
                print(body[:600])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n=== {label} (HTTP {e.code}) ===")
        print(body[:600])
    except Exception as e:
        print(f"\n=== {label} — ERROR: {e} ===")


# 1. Fetch rows from interview_logs (limit 1, to see column shape)
fetch("interview_logs?limit=1", "interview_logs rows (sample)")

# 2. Fetch OpenAPI schema to see all columns
fetch("?select=*", "Root schema list")
