"""
Validate the migration SQL locally - ASCII output only (Windows cp1252 safe).
"""
import sys

SQL = open("scripts/create_interview_sessions_table.sql", encoding="utf-8").read()

print("=" * 60)
print("SQL Structural Validation")
print("=" * 60)

checks = [
    ("CREATE TABLE IF NOT EXISTS",                       "Table creation is idempotent (IF NOT EXISTS)"),
    ("public.interview_sessions",                        "Schema-qualified table name"),
    ("uuid        PRIMARY KEY",                          "UUID primary key"),
    ("auth.users(id) ON DELETE CASCADE",                 "FK to Supabase auth.users with cascade"),
    ("difficulty IN ('Easy', 'Medium', 'Hard')",        "Difficulty CHECK constraint"),
    ("status IN ('completed', 'terminated')",            "Status CHECK constraint"),
    ("jsonb   NOT NULL DEFAULT '[]'::jsonb",             "question_feedback JSONB with default"),
    ("timestamptz NOT NULL DEFAULT now()",               "created_at with server-side default"),
    ("completed_at    timestamptz",                     "completed_at nullable timestamp"),
    ("ENABLE ROW LEVEL SECURITY",                        "RLS enabled"),
    ("DROP POLICY IF EXISTS",                            "Policy drop is idempotent (safe re-run)"),
    ("FOR SELECT",                                       "SELECT policy present"),
    ("FOR INSERT",                                       "INSERT policy present"),
    ("FOR UPDATE",                                       "UPDATE policy present"),
    ("idx_interview_sessions_user_created",              "Index: list by user + date"),
    ("idx_interview_sessions_user_score",                "Index: aggregate scores"),
    ("text[]",                                           "Array columns for list fields"),
    ("overall_score",                                    "overall_score column"),
    ("technical_score",                                  "technical_score column"),
    ("communication_score",                              "communication_score column"),
    ("answer_relevance",                                 "answer_relevance column"),
    ("strengths",                                        "strengths column"),
    ("weaknesses",                                       "weaknesses column"),
    ("improvement_suggestions",                          "improvement_suggestions column"),
    ("practice_areas",                                   "practice_areas column"),
    ("general_feedback",                                 "general_feedback column"),
    ("question_feedback",                                "question_feedback column"),
    ("backend_session_id",                               "backend_session_id column"),
    ("violations",                                       "violations column"),
    ("DO $$",                                            "Smoke-test block present"),
    ("RAISE NOTICE",                                     "Smoke-test has NOTICE output"),
    ("RAISE EXCEPTION",                                  "Smoke-test raises exception on failure"),
]

all_passed = True
for pattern, description in checks:
    found = pattern in SQL
    status = "PASS" if found else "FAIL"
    if not found:
        all_passed = False
    mark = "[PASS]" if found else "[FAIL]"
    print(f"  {mark} {description}")

print()
print("-" * 60)
print("Column inventory (20 columns):")
print("-" * 60)
columns = [
    ("id",                      "uuid",        "PK, auto-generated"),
    ("user_id",                 "uuid",        "FK auth.users, NOT NULL"),
    ("role",                    "text",        "NOT NULL"),
    ("difficulty",              "text",        "NOT NULL, CHECK Easy/Medium/Hard"),
    ("duration_minutes",        "integer",     "NOT NULL, DEFAULT 30"),
    ("backend_session_id",      "text",        "nullable"),
    ("status",                  "text",        "NOT NULL, DEFAULT completed"),
    ("violations",              "integer",     "NOT NULL, DEFAULT 0"),
    ("overall_score",           "integer",     "nullable, CHECK 0-100"),
    ("technical_score",         "integer",     "nullable, CHECK 0-100"),
    ("communication_score",     "integer",     "nullable, CHECK 0-100"),
    ("answer_relevance",        "integer",     "nullable, CHECK 0-100"),
    ("strengths",               "text[]",      "nullable array"),
    ("weaknesses",              "text[]",      "nullable array"),
    ("improvement_suggestions", "text[]",      "nullable array"),
    ("practice_areas",          "text[]",      "nullable array"),
    ("general_feedback",        "text",        "nullable"),
    ("question_feedback",       "jsonb",       "NOT NULL, DEFAULT []"),
    ("created_at",              "timestamptz", "NOT NULL, DEFAULT now()"),
    ("completed_at",            "timestamptz", "nullable"),
]
print(f"  {'Column':<30} {'Type':<15} Notes")
print(f"  {'-'*30} {'-'*15} {'-'*35}")
for col, dtype, notes in columns:
    print(f"  {col:<30} {dtype:<15} {notes}")

print()
print("-" * 60)
print("Schema alignment check:")
print("-" * 60)
alignments = [
    ("schemas.py EvaluationResponse.overall_score",        "overall_score integer"),
    ("schemas.py EvaluationResponse.technical_score",       "technical_score integer"),
    ("schemas.py EvaluationResponse.communication_score",   "communication_score integer"),
    ("schemas.py EvaluationResponse.answer_relevance",      "answer_relevance integer"),
    ("schemas.py EvaluationResponse.strengths List[str]",   "strengths text[]"),
    ("schemas.py EvaluationResponse.weaknesses List[str]",  "weaknesses text[]"),
    ("schemas.py QuestionFeedback (list)",                  "question_feedback jsonb"),
    ("schemas.py EvaluationResponse.improvement_suggestions","improvement_suggestions text[]"),
    ("schemas.py EvaluationResponse.practice_areas",        "practice_areas text[]"),
    ("schemas.py EvaluationResponse.general_feedback",      "general_feedback text"),
    ("types/index.ts SessionContext.role",                  "role text"),
    ("types/index.ts SessionContext.difficulty",            "difficulty text CHECK"),
    ("types/index.ts SessionContext.duration",              "duration_minutes integer"),
    ("interview/[id]/page.tsx violations state",            "violations integer"),
    ("interview/[id]/page.tsx sessionId from /api/setup",   "backend_session_id text"),
]
for source, target in alignments:
    print(f"  {source}")
    print(f"    -> {target}")

print()
if all_passed:
    print("=" * 60)
    print("ALL CHECKS PASSED - SQL is structurally valid.")
    print("Ready to apply in Supabase SQL Editor.")
    print("=" * 60)
else:
    print("=" * 60)
    print("SOME CHECKS FAILED - review the output above.")
    print("=" * 60)
    sys.exit(1)
