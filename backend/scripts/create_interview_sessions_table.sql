-- =============================================================
-- Migration: Create interview_sessions table
-- Project:   PreMock AI
-- Date:      2026-09-18
--
-- Data structure rationale:
--   Scalar fields (role, difficulty, scores) → native columns for
--   fast filtering, ordering, and aggregation (dashboard stats).
--
--   question_feedback → JSONB array of
--     { question: str, answer: str, score: int, feedback: str }
--     Matches backend QuestionFeedback schema exactly (schemas.py L30-35).
--
--   strengths, weaknesses, improvement_suggestions, practice_areas
--   → text[] (Postgres native array) — simple string lists,
--     directly match EvaluationResponse (schemas.py L44-48).
--
-- NOTE: Run this once in the Supabase SQL editor.
--       It is idempotent — safe to re-run.
-- =============================================================


-- ---------------------------------------------------------------
-- 1. Create the table (idempotent via IF NOT EXISTS)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.interview_sessions (

    -- Primary key
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Owner — links to Supabase Auth user
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Session context (from SessionContext type in interview/[id]/page.tsx L11
    --                  and SetupRequest in schemas.py L12-16)
    role            text        NOT NULL,
    difficulty      text        NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    duration_minutes integer    NOT NULL DEFAULT 30,

    -- Backend session id (UUID string returned by POST /api/setup)
    -- Lets us look up the in-memory engine if still alive
    backend_session_id text,

    -- Status of this session
    status          text        NOT NULL DEFAULT 'completed'
                                CHECK (status IN ('completed', 'terminated')),

    -- Proctoring
    violations      integer     NOT NULL DEFAULT 0,

    -- -------------------------------------------------------
    -- Scores — match EvaluationResponse fields (schemas.py L40-43)
    -- -------------------------------------------------------
    overall_score          integer CHECK (overall_score BETWEEN 0 AND 100),
    technical_score        integer CHECK (technical_score BETWEEN 0 AND 100),
    communication_score    integer CHECK (communication_score BETWEEN 0 AND 100),
    answer_relevance       integer CHECK (answer_relevance BETWEEN 0 AND 100),

    -- -------------------------------------------------------
    -- List fields — native Postgres arrays (schemas.py L44-48)
    -- -------------------------------------------------------
    strengths              text[],
    weaknesses             text[],
    improvement_suggestions text[],
    practice_areas         text[],

    -- -------------------------------------------------------
    -- Narrative text (schemas.py L49)
    -- -------------------------------------------------------
    general_feedback       text,

    -- -------------------------------------------------------
    -- Per-question Q&A + feedback
    -- JSONB array: [{question, answer, score, feedback}, ...]
    -- Matches QuestionFeedback model (schemas.py L30-35)
    -- -------------------------------------------------------
    question_feedback      jsonb   NOT NULL DEFAULT '[]'::jsonb,

    -- -------------------------------------------------------
    -- Emotion and Attention Tracking
    -- -------------------------------------------------------
    angry_expr             DOUBLE PRECISION,
    disgust_expr           DOUBLE PRECISION,
    fear_expr              DOUBLE PRECISION,
    happy_expr             DOUBLE PRECISION,
    neutral_expr           DOUBLE PRECISION,
    sad_expr               DOUBLE PRECISION,
    surprise_expr          DOUBLE PRECISION,
    eye_contact            DOUBLE PRECISION,
    face_present           DOUBLE PRECISION,

    -- -------------------------------------------------------
    -- Timestamps
    -- -------------------------------------------------------
    created_at      timestamptz NOT NULL DEFAULT now(),
    completed_at    timestamptz
);

-- ---------------------------------------------------------------
-- 1.5 Add emotion tracking columns if table already existed
-- (Ensures idempotency for existing tables)
-- ---------------------------------------------------------------
ALTER TABLE public.interview_sessions 
    ADD COLUMN IF NOT EXISTS angry_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS disgust_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS fear_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS happy_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS neutral_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS sad_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS surprise_expr DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS eye_contact DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS face_present DOUBLE PRECISION;

-- ---------------------------------------------------------------
-- 2. Indexes for common query patterns
-- ---------------------------------------------------------------

-- Dashboard history: latest sessions for a user
CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_created
    ON public.interview_sessions (user_id, created_at DESC);

-- Stats aggregation: scores per user
CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_score
    ON public.interview_sessions (user_id, overall_score);

-- ---------------------------------------------------------------
-- 3. Row Level Security
-- ---------------------------------------------------------------
ALTER TABLE public.interview_sessions ENABLE ROW LEVEL SECURITY;

-- Drop policies first so this script is safely re-runnable
DROP POLICY IF EXISTS "Users can view own sessions"   ON public.interview_sessions;
DROP POLICY IF EXISTS "Users can insert own sessions" ON public.interview_sessions;
DROP POLICY IF EXISTS "Users can update own sessions" ON public.interview_sessions;

-- SELECT: a user can only read rows they own
CREATE POLICY "Users can view own sessions"
    ON public.interview_sessions
    FOR SELECT
    USING (auth.uid() = user_id);

-- INSERT: a user can only create rows for themselves
CREATE POLICY "Users can insert own sessions"
    ON public.interview_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- UPDATE: a user can only update their own rows
--   (needed if we ever patch status / scores after saving)
CREATE POLICY "Users can update own sessions"
    ON public.interview_sessions
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------
-- 4. Smoke-test: verify the table and policies were created
-- ---------------------------------------------------------------
DO $$
DECLARE
    tbl_count  integer;
    pol_count  integer;
    idx_count  integer;
BEGIN
    SELECT COUNT(*) INTO tbl_count
      FROM information_schema.tables
     WHERE table_schema = 'public'
       AND table_name   = 'interview_sessions';

    SELECT COUNT(*) INTO pol_count
      FROM pg_policies
     WHERE schemaname = 'public'
       AND tablename  = 'interview_sessions';

    SELECT COUNT(*) INTO idx_count
      FROM pg_indexes
     WHERE schemaname = 'public'
       AND tablename  = 'interview_sessions';

    IF tbl_count = 0 THEN
        RAISE EXCEPTION 'FAIL: interview_sessions table was NOT created.';
    ELSE
        RAISE NOTICE 'OK: interview_sessions table exists.';
    END IF;

    IF pol_count < 3 THEN
        RAISE EXCEPTION 'FAIL: Expected 3 RLS policies, found %.', pol_count;
    ELSE
        RAISE NOTICE 'OK: % RLS policies found.', pol_count;
    END IF;

    IF idx_count < 2 THEN
        RAISE NOTICE 'WARN: Expected at least 2 indexes, found %.', idx_count;
    ELSE
        RAISE NOTICE 'OK: % indexes found.', idx_count;
    END IF;
END $$;
