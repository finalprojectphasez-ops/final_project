# Research Experiments Report (Workspace: MY_PART)

**Project Title:** AI-Powered Video Interview Practice Platform with Automated Performance Evaluation and Personalized Feedback Reports — PreMock AI  
**Workspace Identifier:** `MY_PART`  
**Authoritative Rubric:** `interview_practice_100_v1` (Strict 100.0 Marks Maximum; Legacy 110-Point Capped Engine Excluded)  
**Execution Date:** October 2026 (Local Time: 2026-10-13)  
**Repository Commit:** `b5e261ede09a125d060dd4faae22eaf5632c9254`  
**Execution Target Path:** [`research_experiments/experiment_report_MY_PART.md`](file:///d:/nishanth_work/final_project/research_experiments/experiment_report_MY_PART.md)  

---

## Executive Summary

| Experiment | Purpose | Sample Size | Actual Result | Status | Primary Evidence Path |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **EXPERIMENT 1**<br>Workflow & Rubric Correctness | Verify state machine, 18-combination matrix, invariant rules, quotation verification, topic weighting, and missing signals. | 10 unit tests + 18 matrix sessions + 7 invariant audits | **ALL PASS (100%)**<br>- 10/10 unit tests passing (0.013s)<br>- 18/18 role-diff matrix passing<br>- Quote matching flags hallucinations<br>- Equal topic weights proven ($50\%$ each) | **EXECUTED** | [`research_experiments/experiment_1_workflow_rubric/experiment_1_results.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_1_workflow_rubric/experiment_1_results.json) |
| **EXPERIMENT 2**<br>Automated Scoring vs Human Reviewers | Double-blind pilot benchmarking agreement between automated rubric ratings and independent human reviewers using weighted Cohen's $\kappa$ and MAE. | 35 pilot candidate responses across 6 roles | **Formulas Validated; Templates Prepared**<br>- Quadratic $\kappa_w$ formula verified ($\kappa=1.0, 0.9412, -1.0$)<br>- Analytical MAE verified (3.0)<br>- Blank double-blind templates generated<br>- Zero synthetic ratings invented | **PENDING HUMAN INPUT** | [`research_experiments/experiment_2_human_evaluation/experiment_2_pilot_status.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/experiment_2_pilot_status.json) |
| **EXPERIMENT 3**<br>Question & Feedback Quality | Audit question repetition, hallucinated feedback assertions, and prepare 1–5 Likert human review protocol. | 72 session questions audited + 35 pilot items prepared | **0.0% Repetition; 100% Grounding**<br>- Exact duplicate questions: 0<br>- Near-duplicate questions: 0<br>- Unsupported feedback claims: 0<br>- Likert template prepared | **PENDING HUMAN INPUT**<br>*(Automated Audits: EXECUTED)* | [`research_experiments/experiment_3_quality_evaluation/quality_metrics_summary.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_3_quality_evaluation/quality_metrics_summary.json) |
| **EXPERIMENT 4**<br>End-to-End Integration & Services | Run complete multi-turn text session, verify persistence/retrieval, and audit audiovisual models on actual hardware. | 1 complete 5-turn session + 6 platform capabilities audited | **Text Pipeline Functional; Checkpoints Absent**<br>- Text interview created, evaluated (52.5/95.0), persisted, and retrieved<br>- Gaze (8001), Emotion (8002), ASR (8003) offline due to missing local weights | **EXECUTED** | [`research_experiments/experiment_4_integration/integration_results.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_4_integration/integration_results.json) |

---

## EXPERIMENT 1 — Interview Workflow and Rubric Correctness

### 1.1 Purpose
To verify the structural correctness, phase sequencing, invariant constraints, quotation grounding, topic group aggregation, and partial scoring mechanics of PreMock AI's local interview state machine and the authoritative `interview_practice_100_v1` rubric.

### 1.2 Procedure
1. **Existing Rubric Test Suite:** Executed `backend/tests/test_rubric_100.py` via `unittest.TextTestRunner`.
2. **Scripted Role-Difficulty Matrix:** Instantiated 18 distinct test sessions covering all 6 canonical roles (`full_stack_engineer`, `frontend_developer`, `backend_engineer`, `devops_sre`, `ml_engineer`, `data_analyst`) and all 3 seniority difficulty levels (`beginner`, `intermediate`, `advanced`).
3. **Multi-Turn Phased Simulation:** Fed realistic domain candidate responses across turns to trace phase transitions (`intro` $\rightarrow$ `general` $\rightarrow$ `technical`).
4. **Follow-Up Invariant Testing:** Verified that follow-up probes reference candidate answers, increment the follow-up counter, and strictly enforce the ceiling of maximum 2 follow-ups per topic (`followups_used <= 2`), resetting to 0 upon topic advance.
5. **Controlled Clock Deadline Simulation:** Artificially expired the session deadline timestamp (`deadline_timestamp < time.time()`) to verify automatic session termination (`action = "end"`, `is_complete = True`).
6. **Information Leakage Guard:** Verified that `expected_points` is strictly stripped from candidate API responses (`CandidateQuestionResponse`) and history representations.
7. **Evidence Quotation Verification:** Tested verbatim quotation matching versus fabricated evidence strings using `LocalRubricEvaluator.verify_evidence_quote`.
8. **Topic Group Aggregation Invariant:** Evaluated an unbalanced turn history (Topic 1: 1 turn, Rating 4.0 vs Topic 2: 4 turns, Rating 2.0) to prove mathematically that follow-up turns do NOT inflate topic voting weight.
9. **Missing Signals Partial Assessment:** Tested text-only sessions (`spoken_delivery = None`) and all-missing sessions against the documented 100-mark calculator rules.

### 1.3 Sample Size
- **Existing Unit Tests:** 10 test methods in [`backend/tests/test_rubric_100.py`](file:///d:/nishanth_work/final_project/backend/tests/test_rubric_100.py).
- **Scripted Matrix Combinations:** 18 distinct sessions (6 roles $\times$ 3 difficulty levels).
- **Simulated Turns:** 90 individual turn submissions across matrix sessions.
- **Quotation Verification Tests:** 2 test cases (1 verbatim valid, 1 fabricated).
- **Aggregation Invariant Tests:** 2 comparative conditions (Topic-Group vs Naive Turn).
- **Missing Signal Conditions:** 3 states (Partial text-only, All-missing unassessed, Complete).

### 1.4 Actual Results
1. **Unit Test Suite:** **10/10 PASS** in 0.013 seconds.
2. **Matrix Invariants (18/18 Combinations PASS):**
   - **Introduction Occurs Once:** Verified in 18/18 sessions. `topic_plan[0]["phase"] == "intro"`; exactly 1 intro phase topic generated per session.
   - **General Questions Precede Technical:** Verified in 18/18 sessions. General role questions (motivation/teamwork) appear at plan index 1; technical taxonomy topics appear at plan index 2+.
   - **Role & Difficulty Authority:** 18/18 sessions maintained exact selected role taxonomy and normalized difficulty without cross-role pollution.
   - **Follow-up Limits:** 18/18 sessions maintained `followups_used <= 2`. System advanced to `next_topic` or `end` after 2 follow-ups.
   - **Simulated Clock Deadline Handling:** 18/18 sessions reached `action = "end"`, `is_complete = True`, and `status = "completed"` when deadline expired.
   - **Information Leakage Guard:** 18/18 sessions confirmed `expected_points` was completely absent from candidate payloads.
3. **Quotation Verification:**
   - Verbatim transcript quote (`"we update the local cache immediately"`): **VERIFIED (True)**.
   - Fabricated transcript quote (`"we used multi-threaded C++ shared memory buffers"`): **FLAGGED (False)**.
4. **Topic Group Aggregation Invariant:**
   - Topic Group Aggregated Rating: **3.00** (Topic 1: 4.0 $\times$ 50% + Topic 2: 2.0 $\times$ 50%).
   - Naive Turn Averaged Rating: **2.40** (Biased downwards by the 3 extra follow-ups in Topic 2).
   - **Mathematical Invariant Holds:** Each topic received exactly 50.0% weight regardless of follow-up density.
5. **Missing Signals Handling:**
   - Text-only (`spoken_delivery = None`): `assessment_status = "partial"`, `assessed_maximum = 95.0`, `total_score_100 = null`, `provisional_normalized_100` computed, `coverage_percent = 95.0%`.
   - All criteria null: `assessment_status = "unassessed"`, `total_score_100 = null`, `coverage_percent = 0.0%`.
   - Complete signals: `assessment_status = "complete"`, `assessed_maximum = 100.0`, `total_score_100 = 100.0`.

### 1.5 Evidence Paths
- Execution Script: [`research_experiments/experiment_1_workflow_rubric/run_experiment_1.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_1_workflow_rubric/run_experiment_1.py)
- Unittest Wrapper: [`research_experiments/experiment_1_workflow_rubric/test_experiment_1_workflow_rubric.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_1_workflow_rubric/test_experiment_1_workflow_rubric.py)
- Machine-Readable Results: [`research_experiments/experiment_1_workflow_rubric/experiment_1_results.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_1_workflow_rubric/experiment_1_results.json)
- Raw Console Log: [`research_experiments/raw_logs/experiment_1_raw_output.txt`](file:///d:/nishanth_work/final_project/research_experiments/raw_logs/experiment_1_raw_output.txt)
- Individual Session Traces: Directory [`research_experiments/experiment_1_workflow_rubric/session_traces/`](file:///d:/nishanth_work/final_project/research_experiments/experiment_1_workflow_rubric/session_traces/) (18 JSON files).

### 1.6 Limitations
- Tests used scripted domain responses and synthetic simulation clocks; they represent deterministic behavioral and algebraic verifications rather than human user studies.

### 1.7 Status
**EXECUTED**

---

## EXPERIMENT 2 — Automated Scoring Versus Human Reviewers

### 2.1 Purpose
To benchmark the agreement between automated rubric evaluations and independent human reviewers on a pilot dataset of 35 diverse interview responses across all 6 professional roles, using weighted Cohen's Kappa ($\kappa_w$) per criterion and total-score Mean Absolute Error (MAE).

### 2.2 Procedure
1. **Pilot Dataset Compilation:** Assembled 35 diverse interview responses covering all 6 canonical roles and 3 difficulty levels with varied response quality (strong explanations, partial explanations, and non-answers/knowledge gaps).
2. **Double-Blind Packet Preparation:** Compiled [`blinded_review_packet.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/blinded_review_packet.json) containing `item_id`, `role`, `difficulty`, `question`, and `candidate_answer`. **Automated scores were strictly blinded and excluded.**
3. **Human Reviewer Template Generation:** Created identical, blank CSV scoring sheets for Reviewer 1 and Reviewer 2 ([`review_scoring_template_reviewer1.csv`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/review_scoring_template_reviewer1.csv) and [`review_scoring_template_reviewer2.csv`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/review_scoring_template_reviewer2.csv)).
4. **Anchor Guidelines Document:** Formulated [`review_packet_instructions.md`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/review_packet_instructions.md) with exact 0–4 integer anchor definitions for all criteria under `interview_practice_100_v1`.
5. **Automated Baseline Reference:** Pre-computed automated rubric evaluations for all 35 items into a separate reference file ([`automated_scores_blinded_reference.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/automated_scores_blinded_reference.json)).
6. **Statistical Analysis Engine:** Developed [`analyze_human_rubric_agreement.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/analyze_human_rubric_agreement.py) implementing quadratic/linear weighted Cohen's $\kappa$ and total-score MAE.
7. **Strict Non-Fabrication Rule:** In accordance with research integrity requirements, **zero synthetic human ratings were generated by AI**. The experiment analysis engine validated the blank templates and recorded the experiment as awaiting human independent review.

### 2.3 Sample Size
- **Pilot Study Responses:** $N = 35$ unique candidate interview answers.
- **Roles Represented:** Full Stack Engineer (6), Frontend Developer (6), Backend Engineer (6), DevOps / SRE (6), ML Engineer (6), Data Analyst (5).
- **Criteria Evaluated per Item:** 6 text-eligible criteria (`technical_knowledge`, `problem_solving`, `practical_application`, `relevance_completeness`, `communication_clarity`, `followup_reflection`).

### 2.4 Actual Results
1. **Mathematical Formula Calibration Fixtures:**
   - Perfect Agreement Calibration: $\kappa_w = 1.0000$ (**PASS**).
   - Adjacent Off-by-One Agreement Calibration: $\kappa_w = 0.9412$ (**PASS**).
   - Complete Inverse Disagreement Calibration: $\kappa_w = -1.0000$ (**PASS**).
   - Total-Score MAE Analytical Calibration: $\text{MAE} = 3.0000$ Marks (**PASS**).
2. **Human Template Status:**
   - Reviewer 1 Sheet: Blank template generated (35 rows unpopulated).
   - Reviewer 2 Sheet: Blank template generated (35 rows unpopulated).
   - Automated Reference Scores: 35 baseline items scored and preserved.
   - Status: Both templates validated; mathematical engine ready to compute $\kappa_w$ and MAE immediately upon receiving completed human CSV files.

### 2.5 Evidence Paths
- Packet Preparation Script: [`research_experiments/experiment_2_human_evaluation/prepare_experiment_2_packet.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/prepare_experiment_2_packet.py)
- Analysis Engine: [`research_experiments/experiment_2_human_evaluation/analyze_human_rubric_agreement.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/analyze_human_rubric_agreement.py)
- Blinded Review Packet: [`research_experiments/experiment_2_human_evaluation/blinded_review_packet.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/blinded_review_packet.json)
- Reviewer 1 Blank Template: [`research_experiments/experiment_2_human_evaluation/review_scoring_template_reviewer1.csv`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/review_scoring_template_reviewer1.csv)
- Reviewer 2 Blank Template: [`research_experiments/experiment_2_human_evaluation/review_scoring_template_reviewer2.csv`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/review_scoring_template_reviewer2.csv)
- Instructions Guide: [`research_experiments/experiment_2_human_evaluation/review_packet_instructions.md`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/review_packet_instructions.md)
- Automated Baseline Scores: [`research_experiments/experiment_2_human_evaluation/automated_scores_blinded_reference.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/automated_scores_blinded_reference.json)
- Experiment Status Report: [`research_experiments/experiment_2_human_evaluation/experiment_2_pilot_status.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_2_human_evaluation/experiment_2_pilot_status.json)
- Raw Console Log: [`research_experiments/raw_logs/experiment_2_raw_output.txt`](file:///d:/nishanth_work/final_project/research_experiments/raw_logs/experiment_2_raw_output.txt)

### 2.6 Limitations
- Actual human agreement figures cannot be reported until two qualified human interview evaluators independently score the 35 blinded responses.

### 2.7 Status
**PENDING HUMAN INPUT**

---

## EXPERIMENT 3 — Question and Feedback Quality

### 3.1 Purpose
To audit the platform for question repetition and unsupported feedback assertions, and to establish an independent human rating protocol (1–5 Likert scale) for follow-up relevance, answer grounding, and feedback usefulness.

### 3.2 Procedure
1. **Automated Question Repetition Audit:** Inspected all question instances across the 18 session traces from Experiment 1. Computed exact string matches and pairwise Jaccard token overlap across all turns within each session. Flagged any pairwise similarity $> 0.85$.
2. **Automated Feedback Grounding Audit:** Inspected saved interview reports on disk. Evaluated every feedback justification and extracted evidence quotation against the candidate's actual utterance transcripts using verbatim substring matching.
3. **Human Quality Protocol Formulation:** Created [`quality_rating_template.csv`](file:///d:/nishanth_work/final_project/research_experiments/experiment_3_quality_evaluation/quality_rating_template.csv) covering 35 pilot items with 1–5 rating scales for:
   - Follow-up relevance (1 = disconnected, 5 = highly probing and context-grounded)
   - Answer grounding (1 = unrelated, 5 = strictly grounded in candidate transcript)
   - Feedback usefulness (1 = generic, 5 = highly actionable)
4. **Research Scope Governance:** Formally documented that human usefulness ratings reflect subjective candidate satisfaction and do **not** establish improved interview performance.

### 3.3 Sample Size
- **Questions Audited for Repetition:** 72 total question prompts across 18 multi-turn sessions.
- **Reports Audited for Grounding:** All persisted session reports on disk.
- **Human Likert Evaluation Items:** 35 pilot study question-answer items.

### 3.4 Actual Results
1. **Question Repetition Audit:**
   - Exact Duplicate Questions Count: **0**
   - Near-Duplicate Questions Count (Jaccard $> 0.85$): **0**
   - **Repetition Rate:** **0.0%**
2. **Feedback Grounding Audit:**
   - Unsupported Feedback Statements Count: **0**
   - Fabricated Quotations Count: **0**
   - **Grounding Fidelity:** **100.0%**
3. **Human Quality Evaluation Template:**
   - Template generated with 35 pilot rows across 3 Likert dimensions.
   - Awaiting external human review ratings.

### 3.5 Evidence Paths
- Quality Audit Script: [`research_experiments/experiment_3_quality_evaluation/evaluate_question_feedback_quality.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_3_quality_evaluation/evaluate_question_feedback_quality.py)
- Quality Summary JSON: [`research_experiments/experiment_3_quality_evaluation/quality_metrics_summary.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_3_quality_evaluation/quality_metrics_summary.json)
- Human Likert Rating Template: [`research_experiments/experiment_3_quality_evaluation/quality_rating_template.csv`](file:///d:/nishanth_work/final_project/research_experiments/experiment_3_quality_evaluation/quality_rating_template.csv)
- Raw Console Log: [`research_experiments/raw_logs/experiment_3_raw_output.txt`](file:///d:/nishanth_work/final_project/research_experiments/raw_logs/experiment_3_raw_output.txt)

### 3.6 Limitations
- Automated audits verify lexical non-repetition and verbatim grounding; qualitative perceptual dimensions (e.g. nuanced pedagogical usefulness) require human evaluation.
- Per experimental protocol, usefulness ratings reflect subjective perception and do not establish improved candidate interview performance.

### 3.7 Status
**PENDING HUMAN INPUT** *(Automated Repetition and Grounding Audits: EXECUTED)*

---

## EXPERIMENT 4 — End-to-End Integration and Multimodal Service Verification

### 4.1 Purpose
To execute a complete multi-turn text interview validating real-time scoring, report persistence, and retrieval, and to conduct an empirical audit of the platform's audiovisual microservices to determine which capabilities are measured, unavailable, or mocked.

### 4.2 Procedure
1. **End-to-End Text Interview Execution:**
   - Initialized session `e2e_integration_575280` (`Backend Engineer`, `intermediate`, 15 minutes).
   - Executed 5 scripted candidate turns across phases:
     - Turn 1 (Intro): Self-introduction overview
     - Turn 2 (Intro Probe 1): Experience in high-throughput payment pipelines
     - Turn 3 (Intro Probe 2): FastAPI, SQLAlchemy, and asyncpg stack
     - Turn 4 (Technical Main): POST idempotency keys, Redis SETNX atomic locks, and 24h TTL
     - Turn 5 (Technical Probe): Postgres unique constraints on partition/crash fallback
   - Evaluated completed turns using `LocalRubricEvaluator` and `TopicGroup` aggregator.
   - Calculated scores using `compute_rubric_assessment` (`interview_practice_100_v1`).
   - Persisted JSON report to [`backend/data/reports/e2e_integration_575280.json`](file:///d:/nishanth_work/final_project/backend/data/reports/e2e_integration_575280.json).
   - Retrieved report from disk and validated all 7 criteria, partial scoring bounds, and normalized score calculation.
2. **Audiovisual and ML Services Hardware Audit:**
   - Tested TCP port connectivity on Ports 8000, 8001, 8002, and 8003.
   - Inspected local disk for required binary model weights:
     - `gaze_model.keras`
     - `emotion_model.keras`
     - `whisper_indian_accent_lora_20k`
   - Inspected posture and prosody modules for presence of real DSP or computer vision models.
   - Classified every platform output as **MEASURED**, **UNAVAILABLE**, or **MOCKED**.

### 4.3 Sample Size
- **End-to-End Sessions:** 1 complete 5-turn session with disk persistence and retrieval.
- **Microservices Audited:** 6 distinct subsystem capabilities across 4 service ports.

### 4.4 Actual Results
1. **Text Pipeline Integration (PASS):**
   - Session ID: `e2e_integration_575280`
   - Total Turns Executed: 5
   - Topic Groups Detected: 2 (Topic 1: Intro + 2 probes; Topic 2: Technical + 1 probe)
   - Assessed Maximum: **95.0 Marks** (Text-only session; spoken delivery excluded)
   - Assessed Score: **52.50 Marks**
   - Total Score (100-scale): `null` (Strictly avoided presenting 95-mark score as 100-mark complete)
   - Provisional Normalized Score: **55.26 / 100**
   - Assessment Status: **`partial`**
   - Report Persistence: Verified on disk ([`backend/data/reports/e2e_integration_575280.json`](file:///d:/nishanth_work/final_project/backend/data/reports/e2e_integration_575280.json)).
   - Report Retrieval: Verified with 100% field integrity.
   - Criteria Breakdown:
     - `technical_knowledge`: 3.0 / 4 $\rightarrow$ 22.50 / 30.0 Marks
     - `problem_solving`: 1.0 / 4 $\rightarrow$ 5.00 / 20.0 Marks
     - `practical_application`: 2.0 / 4 $\rightarrow$ 7.50 / 15.0 Marks
     - `relevance_completeness`: 1.0 / 4 $\rightarrow$ 2.50 / 10.0 Marks
     - `communication_clarity`: 3.0 / 4 $\rightarrow$ 7.50 / 10.0 Marks
     - `followup_reflection`: 3.0 / 4 $\rightarrow$ 7.50 / 10.0 Marks
     - `spoken_delivery`: `null` (Audio absent)
2. **Audiovisual Services & Output Classification:**

| Capability | Configured Port | Model Checkpoint Path | Exists on Disk? | Service Health | Output Classification |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Core Question & Rubric Engine** | 8000 | `backend/data/interview_dataset.csv` | **YES** | FUNCTIONAL | **MEASURED** |
| **Gaze Estimation (MPIIGaze)** | 8001 | `backend/ml_models/gaze_model.keras` | **NO** | OFFLINE | **UNAVAILABLE** |
| **Facial Emotion (MobileNetV2)** | 8002 | `backend/ml_models/emotion_model.keras` | **NO** | OFFLINE | **UNAVAILABLE** |
| **Whisper ASR Sidecar** | 8003 | `ml/asr_model/whisper_indian_accent_lora_20k` | **NO** | OFFLINE | **UNAVAILABLE** |
| **Posture Analysis** | None | None | **NO** | NOT IMPLEMENTED | **MOCKED / PLACEHOLDER (`null`)** |
| **Voice Acoustic DSP** | None | None | **NO** | NOT IMPLEMENTED | **UNAVAILABLE (DSP) / MEASURED (Lexical counter)** |

> [!IMPORTANT]
> **Key Finding:** A saved report alone is NOT proof that every model ran. The text interview and 100-mark rubric are fully functional. Vision and ASR models require external binary checkpoints to be deployed before live inference can execute.

### 4.5 Evidence Paths
- Integration Runner: [`research_experiments/experiment_4_integration/run_experiment_4.py`](file:///d:/nishanth_work/final_project/research_experiments/experiment_4_integration/run_experiment_4.py)
- Output Session JSON: [`research_experiments/experiment_4_integration/session_output.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_4_integration/session_output.json)
- Persisted Report JSON: [`research_experiments/experiment_4_integration/persisted_report_output.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_4_integration/persisted_report_output.json)
- Machine-Readable Audit: [`research_experiments/experiment_4_integration/integration_results.json`](file:///d:/nishanth_work/final_project/research_experiments/experiment_4_integration/integration_results.json)
- Raw Console Log: [`research_experiments/raw_logs/experiment_4_raw_output.txt`](file:///d:/nishanth_work/final_project/research_experiments/raw_logs/experiment_4_raw_output.txt)

### 4.6 Limitations
- Audiovisual tests verified process health, network connectivity, and checkpoint file existence on the host system; live video/audio inference was blocked by absent weight files.

### 4.7 Status
**EXECUTED** *(Text Pipeline Functional; Audiovisual Sidecars Offline)*

---

## Synthesis and Critical Research Recommendations

1. **Rubric Soundness Confirmed:** The production rubric `interview_practice_100_v1` is mathematically verified: weights total strictly 100.0, topic group aggregation eliminates follow-up bias, quotation verification rejects hallucinations, and partial evaluations strictly enforce the 95-mark ceiling without presenting partial scores as complete.
2. **Legacy 110-Point Score Must Be Retired from Paper:** The paper must exclusively report results under `interview_practice_100_v1`. The legacy function in `llm_engine.py` (which sums to 110 before hard clipping at 100) must be described as an uncalibrated early prototype.
3. **Double-Blind Pilot Study Ready for Human Annotators:** The 35-item evaluation packet and blank templates are prepared and schema-validated. Once two annotators complete their sheets, `analyze_human_rubric_agreement.py` will compute weighted Cohen's $\kappa$ and MAE immediately.
4. **Transparent Multimodal Claims Required:** The paper should claim full implementation of the text-based autonomous question engine and rubric evaluator, while clarifying that multimodal vision and speech modules operate as external microservices requiring separate checkpoint deployments.
