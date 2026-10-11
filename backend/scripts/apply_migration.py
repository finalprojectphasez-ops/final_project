"""
Apply the interview_sessions migration via Supabase Python SDK.

The Python supabase client (v2) exposes .postgrest which is the PostgREST
REST API — it cannot run raw DDL.

However, supabase-py >= 2.x includes a client.rpc() method that can call
Postgres functions, and client.auth is available.

The Supabase Management API (api.supabase.com) requires a personal access
token, not the anon key. So raw DDL must go through:
  1. Supabase SQL Editor (browser — needs login, unavailable here)
  2. psql direct connection string (needs DB password)
  3. Supabase Management API + personal access token

This script will:
  A. Verify connectivity using anon key
  B. Inspect interview_logs columns via a SELECT trick
  C. Attempt to apply DDL via a stored procedure if pg_execute_ddl exists
  D. Otherwise, write the exact connection instructions needed
"""

import os
import sys
from supabase import create_client

SUPABASE_URL = "https://fotdyidbreamqmyhsyfg.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvdGR5aWRicmVhbXFteWhzeWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2MTAxMjMsImV4cCI6MjEwMjE4NjEyM30"
    ".XTxEL1ZJCpamm4VG9rXQKr0aw5TZJp-QHQ7IgwvoUpw"
)

client = create_client(SUPABASE_URL, ANON_KEY)

print("=" * 60)
print("A. Testing connectivity")
print("=" * 60)
try:
    # interview_logs is accessible (returned empty array earlier)
    result = client.table("interview_logs").select("*").limit(1).execute()
    print(f"interview_logs accessible: True, rows={len(result.data)}")
    print(f"Sample data: {result.data}")
except Exception as e:
    print(f"interview_logs error: {e}")

print()
print("=" * 60)
print("B. Checking interview_sessions existence")
print("=" * 60)
try:
    result2 = client.table("interview_sessions").select("*").limit(1).execute()
    print(f"interview_sessions EXISTS. Rows: {len(result2.data)}")
except Exception as e:
    err_str = str(e)
    if "PGRST205" in err_str or "does not exist" in err_str.lower():
        print("interview_sessions does NOT exist (as expected).")
    else:
        print(f"Unexpected error: {e}")

print()
print("=" * 60)
print("C. Attempting DDL via rpc(exec_sql) if available")
print("=" * 60)

DDL = """
CREATE TABLE IF NOT EXISTS public.interview_sessions (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role            text        NOT NULL,
    difficulty      text        NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    duration_minutes integer    NOT NULL DEFAULT 30,
    backend_session_id text,
    status          text        NOT NULL DEFAULT 'completed'
                                CHECK (status IN ('completed', 'terminated')),
    violations      integer     NOT NULL DEFAULT 0,
    eye_contact_violations integer NOT NULL DEFAULT 0,
    face_detection_violations integer NOT NULL DEFAULT 0,
    overall_score          integer CHECK (overall_score BETWEEN 0 AND 100),
    technical_score        integer CHECK (technical_score BETWEEN 0 AND 100),
    communication_score    integer CHECK (communication_score BETWEEN 0 AND 100),
    answer_relevance       integer CHECK (answer_relevance BETWEEN 0 AND 100),
    strengths              text[],
    weaknesses             text[],
    improvement_suggestions text[],
    practice_areas         text[],
    general_feedback       text,
    question_feedback      jsonb   NOT NULL DEFAULT '[]'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    completed_at    timestamptz
);

ALTER TABLE public.interview_sessions
    ADD COLUMN IF NOT EXISTS eye_contact_violations INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS face_detection_violations INTEGER NOT NULL DEFAULT 0;

NOTIFY pgrst, 'reload schema';
"""

try:
    result3 = client.rpc("exec_sql", {"sql": DDL}).execute()
    print(f"exec_sql rpc result: {result3}")
except Exception as e:
    print(f"exec_sql not available (expected): {e}")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print("The anon key cannot run DDL. DDL requires either:")
print("1. Running the SQL file via Supabase Dashboard > SQL Editor")
print("   File: backend/scripts/create_interview_sessions_table.sql")
print()
print("2. Using psql with the direct Postgres connection string:")
print("   Host: db.fotdyidbreamqmyhsyfg.supabase.co")
print("   Port: 5432")
print("   DB:   postgres")
print("   User: postgres")
print("   Pass: [DB password from Supabase Dashboard > Settings > Database]")
print()
print("3. Using the Supabase Management API with a Personal Access Token")
print("   POST https://api.supabase.com/v1/projects/fotdyidbreamqmyhsyfg/database/query")
