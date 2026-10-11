import urllib.request
import json

SUPABASE_URL = "https://fotdyidbreamqmyhsyfg.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvdGR5aWRicmVhbXFteWhzeWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2MTAxMjMsImV4cCI6MjEwMjE4NjEyM30"
    ".XTxEL1ZJCpamm4VG9rXQKr0aw5TZJp-QHQ7IgwvoUpw"
)

url = f"{SUPABASE_URL}/rest/v1/interview_sessions?limit=1"

req = urllib.request.Request(url, headers={
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Accept": "application/json",
})

try:
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read().decode()
        print("Status:", r.status)
        print("Body:", body[:300])
        print()
        print("RESULT: interview_sessions table EXISTS (HTTP 200 returned)")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print("HTTP Error:", e.code, e.reason)
    print("Body:", body[:400])
    print()
    if "42P01" in body or "does not exist" in body.lower():
        print("RESULT: interview_sessions table does NOT exist yet")
    elif e.code == 200:
        print("RESULT: Table exists but returned empty set")
    else:
        print("RESULT: Unexpected error - table status unknown")
except Exception as e:
    print("Network/Other Error:", e)
