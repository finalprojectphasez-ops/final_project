import os
import requests

SUPABASE_URL = "https://fotdyidbreamqmyhsyfg.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvdGR5aWRicmVhbXFteWhzeWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2MTAxMjMsImV4cCI6MjEwMjE4NjEyM30"
    ".XTxEL1ZJCpamm4VG9rXQKr0aw5TZJp-QHQ7IgwvoUpw"
)

# Call the root endpoint of PostgREST which returns OpenAPI spec
res = requests.get(f"{SUPABASE_URL}/rest/v1/", headers={"apikey": ANON_KEY})
print(res.status_code)
spec = res.json()
paths = spec.get("paths", {})
rpc_paths = [p for p in paths if p.startswith("/rpc/")]
print("Available RPCs:", rpc_paths)
