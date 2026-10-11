import os
from supabase import create_client

SUPABASE_URL = "https://fotdyidbreamqmyhsyfg.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvdGR5aWRicmVhbXFteWhzeWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2MTAxMjMsImV4cCI6MjEwMjE4NjEyM30"
    ".XTxEL1ZJCpamm4VG9rXQKr0aw5TZJp-QHQ7IgwvoUpw"
)

client = create_client(SUPABASE_URL, ANON_KEY)

DDL = """
ALTER TABLE public.interview_sessions
ADD COLUMN IF NOT EXISTS eye_contact_violations INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS face_detection_violations INTEGER NOT NULL DEFAULT 0;
NOTIFY pgrst, 'reload schema';
"""

try:
    result = client.rpc("exec_sql", {"sql": DDL}).execute()
    print("SUCCESS!")
    print(result)
except Exception as e:
    print(f"ERROR: {e}")
