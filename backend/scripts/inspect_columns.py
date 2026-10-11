"""
Fetch the column structure of interview_logs by asking PostgREST for its
OpenAPI definition. Since the root requires service_role, we use the
standard PostgREST column-inference trick: select with a non-existent
column to get the list of valid columns in the error hint.

Also: insert a zero-value row using an intentionally wrong type to trigger
a Postgres type-error that reveals column names.
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


def fetch(path: str, label: str, method: str = "GET", data: bytes = None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    hdrs = dict(HEADERS)
    if data:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=hdrs, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode()
            print(f"\n=== {label} (HTTP {r.status}) ===")
            try:
                print(json.dumps(json.loads(body), indent=2)[:1500])
            except Exception:
                print(body[:800])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n=== {label} (HTTP {e.code}) ===")
        print(body[:800])
    except Exception as e:
        print(f"\n=== {label} — ERROR: {e} ===")


# 1. Fetch all rows (empty table but we see the schema via PostgREST Accept-Profile)
fetch("interview_logs?limit=5", "interview_logs - all rows")

# 2. Try selecting a non-existent column to get a hint about valid columns
fetch("interview_logs?select=__nonexistent_col__&limit=1",
      "interview_logs - column probe (error will list valid columns)")

# 3. Try selecting * with column hints header
hdrs2 = dict(HEADERS)
hdrs2["Accept-Profile"] = "public"
url3 = f"{SUPABASE_URL}/rest/v1/interview_logs?select=*&limit=1"
req3 = urllib.request.Request(url3, headers=hdrs2)
try:
    with urllib.request.urlopen(req3, timeout=8) as r:
        body = r.read().decode()
        print(f"\n=== interview_logs SELECT * (HTTP {r.status}) ===")
        print(body[:1500])
except urllib.error.HTTPError as e:
    print(f"\n=== interview_logs SELECT * (HTTP {e.code}) ===")
    print(e.read().decode()[:800])
