# Verified Research Details and Engineering Report (Workspace: MY_PART)

**Project Title:** AI-Powered Video Interview Practice Platform with Automated Performance Evaluation and Personalized Feedback Reports (PreMock AI)  
**Workspace Identifier:** `MY_PART`  
**Report Generated:** October 2026 (Verified against codebase state)  
**Target Repository Path:** `d:/nishanth_work/final_project`  

---

## 1. PROJECT OVERVIEW

### 1.1 Problem Statement and Context
Job applicants preparing for software engineering, technical infrastructure, and data science interviews frequently face significant challenges:
1. **Lack of realistic practice environments:** Static interview question lists do not replicate live, multi-turn conversational exchanges or answer-contingent follow-up probes.
2. **Subjective and uncalibrated feedback:** Human mock interviews are expensive, non-standardized, and prone to evaluator bias, while off-the-shelf generative AI wrappers offer ungrounded, hallucinated scores without verifiable rubrics.
3. **Absence of structured evidence:** Existing practice platforms fail to ground evaluations in verifiable candidate quotations, allowing arbitrary scoring and prompt-injection vulnerabilities.
4. **Conflation of technical competence with audiovisual traits:** Many commercial video interview platforms improperly penalize candidates on technical marks for camera artifacts, gaze deviations, or cultural expression differences.

### 1.2 Objectives
The PreMock AI platform addresses these problems by providing:
- A structured, local mock interview pipeline enforcing a strict multi-turn protocol: Self-Introduction $\rightarrow$ General Role Questions $\rightarrow$ Role-Specific Technical Questions with answer-grounded follow-ups $\rightarrow$ Closing Wrap-up.
- A deterministic, mathematically transparent **100-mark assessment rubric** (`interview_practice_100_v1`) operating with integer anchors (0–4), verified candidate quotations, and equal topic group weighting.
- A strict isolation barrier between core technical scoring (text/speech content) and non-scoring coaching observations (facial expressions, gaze/eye contact, face presence).
- Autonomous, local execution capability without requiring paid cloud inference APIs for core session management and rubric evaluation.

### 1.3 Intended Users
- **Primary:** Job seekers, software engineering students, bootcamp graduates, and transitioning technical professionals preparing for technical screen and system design interviews.
- **Secondary:** Academic career development centers, engineering hiring managers, and mock interview coaches requiring reproducible interview session audits and provenance logs.

### 1.4 Implemented Features Status Breakdown

To ensure empirical fidelity in research reporting, platform functionality in this workspace is classified strictly by verified codebase implementation:

| Functional Area | Verification Status | Verified Evidence File / Reference | Operational Details |
| :--- | :--- | :--- | :--- |
| **Resume Upload & Profile Extraction** | **Completed** | [`backend/app/routes/resume.py`](file:///d:/nishanth_work/final_project/backend/app/routes/resume.py#L20-L68), [`backend/app/services/resume_parser.py`](file:///d:/nishanth_work/final_project/backend/app/services/resume_parser.py) | Parses PDF, DOCX, TXT; extracts 15 validated profile fields without paid APIs. |
| **Authoritative Role & Difficulty Selection** | **Completed** | [`backend/app/services/local_interview_model.py`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L28-L600), [`frontend/src/app/interview/new/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/new/page.tsx#L7-L35) | 6 canonical technical roles; 3 normalized difficulty tiers; 15/30/45 minute session targets. |
| **Phased Interview Session State Machine** | **Completed** | [`backend/app/services/session_manager.py`](file:///d:/nishanth_work/final_project/backend/app/services/session_manager.py#L70-L325) | Intro $\rightarrow$ General $\rightarrow$ Technical flow; question order preserved; deadline precedence enforced. |
| **Dynamic Answer-Grounded Follow-Ups** | **Completed** | [`backend/app/services/local_interview_model.py`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L1144-L1285) | Max 2 follow-ups per topic; counter resets only on new topic; probes grounded in candidate text. |
| **Hidden Evaluation Criteria** | **Completed** | [`backend/app/services/session_manager.py`](file:///d:/nishanth_work/final_project/backend/app/services/session_manager.py#L52-L59), [`backend/app/routes/interview.py`](file:///d:/nishanth_work/final_project/backend/app/routes/interview.py#L52-L72) | `expected_points` stored internally on backend; strictly stripped from candidate API responses. |
| **100-Mark Rubric Calculation Engine** | **Completed** | [`backend/app/rubric/calculator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/calculator.py#L74-L165), [`backend/app/rubric/config.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py#L10-L106) | 7 criteria summing to 100.0 marks; anchors 0–4; partial assessments handle missing signals. |
| **Equal Group-Weighted Aggregation** | **Completed** | [`backend/app/rubric/aggregator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/aggregator.py#L56-L142) | Follow-up turn counts do not inflate topic group weights; arithmetic average across groups. |
| **Candidate Quote Verification** | **Completed** | [`backend/app/rubric/evaluator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L162-L194) | Verifies exact substring match between evidence quote and candidate text; flags hallucinations. |
| **Disk Session & Report Persistence** | **Completed** | [`backend/app/routes/reports.py`](file:///d:/nishanth_work/final_project/backend/app/routes/reports.py#L64-L95), [`backend/app/services/session_manager.py`](file:///d:/nishanth_work/final_project/backend/app/services/session_manager.py#L44-L68) | JSON files written to `backend/data/sessions/` and `backend/data/reports/`. |
| **Human Review Override & CSV/JSON Export** | **Completed** | [`backend/app/routes/rubric.py`](file:///d:/nishanth_work/final_project/backend/app/routes/rubric.py#L65-L189), [`frontend/src/app/report/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/report/[id]/page.tsx#L99-L149) | Manual criterion override API; provenance CSV/JSON exports with candidate quotes and reasons. |
| **Next.js 16 Interview & Proctoring UI** | **Completed** | [`frontend/src/app/interview/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/[id]/page.tsx), [`frontend/src/app/report/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/report/[id]/page.tsx) | Live video canvas, Web Audio frequency bars, browser TTS utterance, warning modals. |
| **MobileNetV2 Emotion Training & Evaluation** | **Completed** | [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json), [`ml/emotion_v2/train_v2.py`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py) | Full training logs and held-out test evaluation on FER-2013 (7,178 test images). |
| **MPIIGaze Threshold Calibration** | **Completed** | [`ml/eye_contact/eye_contact_thresholds.json`](file:///d:/nishanth_work/final_project/ml/eye_contact/eye_contact_thresholds.json) | Calibrated pitch (-0.1528) and yaw (-0.0726) center offsets and bounding thresholds. |
| **Speech-to-Text Streaming & Server Sidecar** | **Partial** | [`ml/asr_service/asr_server.py`](file:///d:/nishanth_work/final_project/ml/asr_service/asr_server.py), [`frontend/src/app/interview/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/[id]/page.tsx#L146-L264) | Client-side WAV recording and streaming chunk proxy complete; backend sidecar script exists; model weights missing locally. |
| **Vision Inference Sidecar Deployment** | **Partial** | [`backend/emotion_service_server.py`](file:///d:/nishanth_work/final_project/backend/emotion_service_server.py), [`backend/gaze_service_server.py`](file:///d:/nishanth_work/final_project/backend/gaze_service_server.py) | Microservice wrappers on ports 8001/8002 implemented; binary `.keras` checkpoints omitted from local workspace. |
| **Voice / Prosody Acoustic Analysis** | **Placeholder** | [`backend/app/rubric/evaluator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L449-L483), [`backend/app/rubric/config.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py#L89-L101) | Criterion `spoken_delivery` defaults to null (partial rubric); acoustic DSP models (jitter, shimmer, pitch) not implemented. |
| **Posture Analysis** | **Placeholder** | [`backend/app/rubric/evaluator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L589-L596), [`frontend/src/app/interview/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/[id]/page.tsx#L743) | Field exists as explicit placeholder (`posture: null`) in schema and coaching feedback; no model exists. |
| **Supabase Cloud Database Synchronization** | **Untested / Mocked** | [`frontend/src/app/interview/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/[id]/page.tsx#L810-L825) | Wrapped in try/catch fallback; local disk JSON and browser session storage operate unconditionally. |

---

## 2. MODULE INVENTORY

The platform architecture comprises ten distinct subsystems:

```
+---------------------------------------------------------------------------------------------------+
|                                      PREMOCK AI MODULE INVENTORY                                   |
+---------------------------------------------------------------------------------------------------+
|  1. Resume Extraction & Role Selection        6. Posture Analysis (Placeholder)                   |
|  2. Question Generation & Dynamic Follow-ups  7. Voice & Prosody Delivery (Rule-based / Review)  |
|  3. Speech-to-Text (ASR)                      8. Answer Content Scoring                           |
|  4. Facial Expression Analysis                9. Deterministic Score Aggregation                  |
|  5. Gaze & Eye-Contact Estimation            10. Personalized Feedback & Provenance Reports       |
+---------------------------------------------------------------------------------------------------+
```

### Module 1: Resume Extraction and Job-Role Selection
- **Purpose:** Ingests candidate resumes, extracts structured professional profiles across 15 fields, and maps candidate skills to authoritative technical domain taxonomies.
- **Status:** **Completed**
- **Method / Model Type:** Rule-based parser + grounded local language modeling. Custom PyPDF2 text extraction followed by regex/lexical entity recognition. Zero external paid APIs.
- **Inputs:** Multipart uploaded resume file (`.pdf`, `.docx`, `.txt`, max 5 MB) or raw text string.
- **Outputs:** `ProfessionalProfile` schema containing 15 fields: `current_title`, `previous_titles`, `current_company`, `previous_companies`, `years_experience`, `seniority`, `primary_domain`, `industries`, `core_skills`, `secondary_skills`, `tools`, `leadership_experience`, `key_achievements`, `location`, `summary`.
- **Main Files / Functions:**
  - Route: [`backend/app/routes/resume.py::upload_resume`](file:///d:/nishanth_work/final_project/backend/app/routes/resume.py#L20-L68)
  - Parser: [`backend/app/services/resume_parser.py::ResumeParser.parse_file`](file:///d:/nishanth_work/final_project/backend/app/services/resume_parser.py)
  - Profile Extractor: [`backend/app/services/local_interview_model.py::extract_resume_profile`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L600-L728)
- **Dependencies:** `PyPDF2>=3.0.1`, `fastapi>=0.115.0`, `pydantic>=2.9.2`.

### Module 2: Interview Question Generation and Dynamic Follow-Ups
- **Purpose:** Manages the phased session state machine (Intro $\rightarrow$ General $\rightarrow$ Technical $\rightarrow$ Closing), generating topic-grounded main questions and adaptive, answer-contingent follow-up probes.
- **Status:** **Completed**
- **Method / Model Type:** Grounded local language model service using canonical role taxonomies, topic exemplars from `backend/data/interview_dataset.csv`, and local token-level Jaccard similarity deduplication ($\text{threshold} = 0.65$).
- **Inputs:** Selected role, normalized difficulty tier, interview duration, candidate profile, conversation history, and latest candidate answer.
- **Outputs:** `InterviewQuestionInternal` (backend private model containing `expected_points`) projected to candidate-facing `CandidateQuestionResponse` (with `expected_points` stripped). Action directive: `follow_up`, `clarify`, `next_topic`, or `end`.
- **Main Files / Functions:**
  - Topic Planning: [`backend/app/services/local_interview_model.py::build_topic_plan`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L900-L950)
  - Main Question Generation: [`backend/app/services/local_interview_model.py::generate_main_question`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L1062-L1139)
  - Follow-up Generation: [`backend/app/services/local_interview_model.py::generate_followup_turn`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L1144-L1285)
  - Session Lifecycle: [`backend/app/services/session_manager.py::submit_turn`](file:///d:/nishanth_work/final_project/backend/app/services/session_manager.py#L136-L326)
- **Dependencies:** Standard library (`re`, `time`, `json`), `fastapi`, `pydantic`.

### Module 3: Speech-to-Text (ASR)
- **Purpose:** Transcribes candidate spoken answers in real-time or turn batches to provide clean text transcripts for rubric evaluation.
- **Status:** **Partial**
- **Method / Model Type:** Fine-tuned ASR pipeline using parameter-efficient fine-tuning (PEFT / LoRA) on `openai/whisper-base.en` (8-bit quantized with `BitsAndBytesConfig`). Sidecar microservice proxy architecture.
- **Inputs:** 16 kHz mono PCM WAV audio stream/chunks sent as `multipart/form-data`.
- **Outputs:** JSON object containing `text` (transcription string), `transcription_time_s`, and audio duration metadata.
- **Main Files / Functions:**
  - Client WAV Recording: [`frontend/src/app/interview/[id]/page.tsx::encodeWAV`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/%5Bid%5D/page.tsx#L146-L177)
  - Backend ASR Proxy: [`backend/app/routes/speech.py::transcribe_local`](file:///d:/nishanth_work/final_project/backend/app/routes/speech.py#L10-L45)
  - ASR Inference Sidecar: [`ml/asr_service/asr_server.py::transcribe`](file:///d:/nishanth_work/final_project/ml/asr_service/asr_server.py#L46-L95)
  - Training Pipeline: [`ml/asr_training/train_full.py`](file:///d:/nishanth_work/final_project/ml/asr_training/train_full.py#L15-L170), [`ml/asr_training/fix_speaker_split.py`](file:///d:/nishanth_work/final_project/ml/asr_training/fix_speaker_split.py)
- **Dependencies:** `fastapi`, `httpx>=0.28.1`, `soundfile>=0.14.0`, `torch`, `transformers`, `peft`, `evaluate`.
- **Missing / Gap:** The LoRA checkpoint weights (`ml/asr_model/whisper_indian_accent_lora_20k`) are not stored locally in this repository workspace (trained on external GPU/Colab). Audio input strictly requires WAV; WebM format returns HTTP 415.

### Module 4: Facial Expression Analysis
- **Purpose:** Classifies candidate facial emotions during the interview for non-scoring practice coaching feedback.
- **Status:** **Completed (Model trained & validated; runtime sidecar proxy implemented)**
- **Method / Model Type:** Fine-tuned deep transfer learning classifier. MobileNetV2 backbone (ImageNet pretrained) fine-tuned on FER-2013 with 7 emotion classes.
- **Inputs:** 96x96x3 RGB webcam frame images (or 48x48 grayscale in v1 baseline).
- **Outputs:** Classified emotion label (`angry`, `disgust`, `fear`, `happy`, `neutral`, `sad`, `surprise`) and float confidence score [0.0, 1.0].
- **Main Files / Functions:**
  - Training Script: [`ml/emotion_v2/train_v2.py`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py)
  - Evaluation Report: [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json)
  - Backend Proxy Route: [`backend/app/routes/emotion.py::predict_emotion`](file:///d:/nishanth_work/final_project/backend/app/routes/emotion.py#L24-L65)
  - Inference Service: [`backend/emotion_service_server.py::predict`](file:///d:/nishanth_work/final_project/backend/emotion_service_server.py#L31-L75)
- **Dependencies:** `tensorflow>=2.15.0`, `keras`, `opencv-python`, `numpy`, `PIL`.
- **Missing / Gap:** Binary weight file `emotion_model_v2.keras` (27.26 MB) was excluded from local Git checkout; evaluation metrics and confusion matrices are fully preserved locally.

### Module 5: Gaze and Eye-Contact Estimation
- **Purpose:** Measures candidate gaze direction (pitch and yaw) and classifies whether the candidate is maintaining eye contact with the camera.
- **Status:** **Completed (Calibration and service implemented; weight binary external)**
- **Method / Model Type:** Two-stage vision pipeline:
  1. Face and landmark detection using MediaPipe FaceMesh (468 landmarks, right eye contour indices 33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246).
  2. Custom CNN gaze regressor (`Conv2D` 32 $\rightarrow$ 64 $\rightarrow$ 128 $\rightarrow$ `Dense` 256 $\rightarrow$ 128 $\rightarrow$ linear 2 units) calibrated on MPIIGaze.
- **Inputs:** Webcam video frames (`multipart/form-data` image bytes).
- **Outputs:** `face_present` (bool), `face_count` (int), `looking_at_camera` (bool), `gaze_pitch` (float), `gaze_yaw` (float).
- **Main Files / Functions:**
  - Threshold Calibration: [`ml/eye_contact/eye_contact_thresholds.json`](file:///d:/nishanth_work/final_project/ml/eye_contact/eye_contact_thresholds.json)
  - Service Layer: [`backend/app/services/gaze_service.py::analyze_gaze`](file:///d:/nishanth_work/final_project/backend/app/services/gaze_service.py#L62-L190)
  - Gaze Sidecar Server: [`backend/gaze_service_server.py`](file:///d:/nishanth_work/final_project/backend/gaze_service_server.py)
  - Training Script: [`ml/eye_contact/train.py`](file:///d:/nishanth_work/final_project/ml/eye_contact/train.py)
- **Calibrated Parameters:**
  - `center_pitch`: -0.15278
  - `center_yaw`: -0.07262
  - `pitch_threshold`: 0.060
  - `yaw_threshold`: 0.075

### Module 6: Posture Analysis
- **Purpose:** Body posture alignment and upper-body slouching detection.
- **Status:** **Placeholder / Not Implemented**
- **Method / Model Type:** None. The schema explicitly designates this signal as unassessed.
- **Inputs:** N/A
- **Outputs:** Explicitly returns `posture: null` in coaching observations.
- **Main Files / Functions:**
  - Schema: [`backend/app/rubric/schemas.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/schemas.py), [`frontend/src/app/interview/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/%5Bid%5D/page.tsx#L743)
- **Dependencies:** None.

### Module 7: Voice / Prosody Analysis
- **Purpose:** Evaluates pacing, speech rate, filler words, and vocal delivery.
- **Status:** **Rule-Based Fallback / Human Review Override**
- **Method / Model Type:** Rule-based lexical filler word counter (`um`, `uh`, `like`, `you know`, `basically`) and verbal word count estimator. Criterion `spoken_delivery` defaults to `null` in automated evaluation, triggering a partial assessment status (95-mark maximum) unless a human manual review override is posted.
- **Inputs:** Transcribed candidate answer utterances and audio recording presence flags.
- **Outputs:** Floating-point rating (0.0–4.0) or `None` if unverified; max 5.0 marks.
- **Main Files / Functions:**
  - Estimation: [`backend/app/rubric/evaluator.py::estimate_spoken_delivery_rating`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L449-L483)
  - Override Endpoint: [`backend/app/routes/rubric.py::manual_criterion_override`](file:///d:/nishanth_work/final_project/backend/app/routes/rubric.py#L65-L129)
- **Dependencies:** Standard library regex (`re`). Advanced acoustic DSP models (Praat/OpenSMILE pitch, jitter, shimmer) are not implemented in this workspace.

### Module 8: Answer / Content Scoring
- **Purpose:** Scores candidate responses against role-specific technical mechanisms, problem-solving structure, practical examples, and question relevance.
- **Status:** **Completed**
- **Method / Model Type:** Deterministic local NLP matching engine. Extracts 200+ normalized technical concepts across 8 engineering domains, detects STAR structural stages (Situation, Task, Action, Result), extracts engineering trade-off keywords, and verifies candidate quotation substrings.
- **Inputs:** Candidate answer text, main interview question, phase, topic group history, and reference expected points.
- **Outputs:** Integer anchor ratings (0, 1, 2, 3, 4), rubric reasoning strings, and verifiable quote dictionaries.
- **Main Files / Functions:**
  - Concept Catalog: [`backend/app/rubric/evaluator.py::TECHNICAL_CONCEPTS_CATALOG`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L42-L97)
  - Topic Group Evaluator: [`backend/app/rubric/evaluator.py::evaluate_topic_group`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L196-L423)
  - Evasion / Non-answer Handler: [`backend/app/rubric/evaluator.py::_build_evasion_group_assessment`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L425-L447)
- **Dependencies:** Standard library (`re`, `math`). Zero paid API dependencies.

### Module 9: Score Aggregation
- **Purpose:** Combines group-level evaluations across multiple interview turns into a unified 100-mark assessment.
- **Status:** **Completed**
- **Method / Model Type:** Mathematical aggregation engine implementing equal group weighting and full floating-point precision calculation:
  $$\text{criterion\_rating} = \frac{1}{|G_{\text{eligible}}|} \sum_{g \in G_{\text{eligible}}} \text{rating}(g)$$
  $$\text{earned\_marks} = \frac{\text{criterion\_rating}}{4.0} \times \text{maximum\_marks}$$
- **Inputs:** Dictionary of criterion ratings across all topic groups.
- **Outputs:** `RubricAssessmentResponse` containing `total_score_100`, `provisional_normalized_100`, `assessment_status` (`complete`, `partial`, `unassessed`), and `coverage_percent`.
- **Main Files / Functions:**
  - Aggregator: [`backend/app/rubric/aggregator.py::aggregate_criterion_ratings_across_groups`](file:///d:/nishanth_work/final_project/backend/app/rubric/aggregator.py#L110-L142)
  - Calculator: [`backend/app/rubric/calculator.py::compute_rubric_assessment`](file:///d:/nishanth_work/final_project/backend/app/rubric/calculator.py#L74-L165)
- **Dependencies:** Standard library `math`.

### Module 10: Personalized Feedback and Report Generation
- **Purpose:** Assembles final evaluation reports combining rubric breakdown, turn-by-turn question feedback, strengths, weaknesses, improvement suggestions, and coaching observations.
- **Status:** **Completed**
- **Method / Model Type:** Template-free report generation engine with triple-redundancy disk persistence.
- **Inputs:** Completed session history, turn evaluations, rubric assessment object, and coaching observations.
- **Outputs:** Comprehensive JSON report saved to `backend/data/reports/${session_id}.json`, cached in browser `sessionStorage`, and formatted for export via CSV or JSON.
- **Main Files / Functions:**
  - Route: [`backend/app/routes/reports.py::save_report`](file:///d:/nishanth_work/final_project/backend/app/routes/reports.py#L64-L95)
  - Backfill Middleware: [`backend/app/routes/reports.py::_ensure_rubric_assessment`](file:///d:/nishanth_work/final_project/backend/app/routes/reports.py#L17-L62)
  - Provenance Export: [`backend/app/routes/rubric.py::export_rubric_provenance`](file:///d:/nishanth_work/final_project/backend/app/routes/rubric.py#L131-L189)
  - Frontend Display: [`frontend/src/app/report/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/report/%5Bid%5D/page.tsx)
- **Dependencies:** `fastapi`, `pydantic`.

---

## 3. ARCHITECTURE AND INTERVIEW FLOW

### 3.1 Technology Stack and Versions
- **Frontend Framework:** Next.js 16.3.1 (App Router), React 19.2.8, React-DOM 19.2.8.
- **Styling:** Tailwind CSS v4 (`@tailwindcss/postcss^4`, `tailwindcss^4`).
- **Language / Typing:** TypeScript 5, Node.js 20+ runtime.
- **Backend Framework:** FastAPI >= 0.115.0, Uvicorn >= 0.30.6.
- **Data Validation & Schemas:** Pydantic >= 2.9.2.
- **Document Processing:** PyPDF2 >= 3.0.1, python-multipart >= 0.0.12.
- **HTTP Client:** HTTPX >= 0.28.1 (async client for sidecar microservice proxies).
- **Machine Learning & Deep Learning:** TensorFlow >= 2.15.0, NumPy >= 1.26.4, Pillow >= 10.2.0, MediaPipe.
- **Database / Storage:** Local filesystem (`JSON`), Browser `sessionStorage`, optional `@supabase/supabase-js^2.112.3` / `supabase>=2.8.1`.

### 3.2 Microservice Topology and Ports
Because TensorFlow initialization can conflict with ASGI async event loops or cause memory contention under Windows, PreMock AI isolates heavyweight deep learning runtimes into dedicated sidecars:
- **Port 8000:** Primary FastAPI Application (`backend/app/main.py`)
- **Port 8001:** MPIIGaze Inference Server (`backend/gaze_service_server.py`)
- **Port 8002:** MobileNetV2 Emotion Inference Server (`backend/emotion_service_server.py`)
- **Port 8003:** Whisper ASR Sidecar (`ml/asr_service/asr_server.py`)
- **Port 3000 / 3001:** Next.js Frontend Application (`frontend/`)

### 3.3 End-to-End System Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Candidate Browser (Next.js 16 / React 19)"]
        UI_Setup["Setup Page (/interview/new)\n- Role & Difficulty Select\n- Resume Upload (.pdf/.docx/.txt)"]
        UI_Interview["Live Proctor Page (/interview/[id])\n- Fullscreen Video & Audio Monitor\n- Live Speech WAV Streamer\n- Browser TTS Audio Player"]
        UI_Report["Report Page (/report/[id])\n- 100-Mark Rubric Breakdown\n- Turn Provenance & Quotes\n- Manual Review & CSV/JSON Export"]
    end

    subgraph Backend["Core PreMock Engine (FastAPI - Port 8000)"]
        R_Resume["Resume Route (/api/resume/upload)\n- PyPDF2 Text Extraction\n- 15-Field Profile Extractor"]
        R_Session["Session Manager (/api/interview/session/*)\n- Phased Topic Planner\n- Turn Policy & Max 2 Follow-ups\n- Private expected_points Filter"]
        R_LocalLLM["Local Interview Model\n- Grounded Question Generator\n- Near-Duplicate Jaccard Filter\n- Adaptive Probe Generator"]
        R_Rubric["Rubric Engine (/api/rubric/*)\n- Concept & STAR Matcher\n- Verifiable Quote Checker\n- Equal Group Aggregator\n- Deterministic Calculator"]
        R_Reports["Reports Route (/api/reports/*)\n- Persistent JSON Storage\n- Rubric Auto-Backfill"]
    end

    subgraph Sidecars["Isolated ML Inference Microservices"]
        ASR_Sidecar["Whisper ASR Sidecar\n(Port 8003 - /transcribe)\n- Whisper-base.en + LoRA 20k"]
        Gaze_Sidecar["Gaze Service\n(Port 8001 - /predict)\n- MPIIGaze CNN Regressor"]
        Emotion_Sidecar["Emotion Service\n(Port 8002 - /predict)\n- MobileNetV2 on FER-2013"]
    end

    subgraph Storage["Persistence Layer"]
        Disk_Sessions[("Local Disk: backend/data/sessions/")]
        Disk_Reports[("Local Disk: backend/data/reports/")]
        Browser_Storage[("Browser: sessionStorage")]
        Cloud_DB[("Optional: Supabase PostgreSQL")]
    end

    %% Interactions
    UI_Setup -->|POST /api/resume/upload| R_Resume
    R_Resume -->|Extract Profile| R_LocalLLM
    UI_Setup -->|POST /api/interview/session/create| R_Session
    R_Session -->|Generate Intro Question| R_LocalLLM
    R_Session -->|Write Session JSON| Disk_Sessions

    UI_Interview -->|POST /api/speech/transcribe-local| Backend
    Backend -->|Proxy Audio WAV| ASR_Sidecar
    UI_Interview -->|POST /api/emotion/predict| Backend
    Backend -->|Proxy Frame| Emotion_Sidecar
    Backend -->|Proxy Eye Crop| Gaze_Sidecar

    UI_Interview -->|POST /api/interview/session/[id]/submit-turn| R_Session
    R_Session -->|Generate Next Question / Probe| R_LocalLLM
    R_Session -->|Update Turn History| Disk_Sessions

    UI_Interview -->|POST /api/rubric/assess| R_Rubric
    UI_Interview -->|POST /api/reports/save| R_Reports
    R_Reports -->|Write Report JSON| Disk_Reports
    UI_Interview -->|Cache Report| Browser_Storage
    UI_Interview -.->|Sync Session| Cloud_DB

    UI_Report -->|GET /api/reports/[id]| R_Reports
    UI_Report -->|POST /api/rubric/manual-review| R_Rubric
```

### 3.4 Operational Interview Lifecycle Flow

The platform executes a strict four-phase sequence:

1. **Setup & Ingestion Phase:**
   - Candidate selects one of 6 authoritative roles and 3 difficulty tiers (Easy/Beginner, Medium/Intermediate, Hard/Advanced).
   - Candidate selects duration (15 min = 4 question target, 30 min = 6 question target, 45 min = 8 question target).
   - Candidate uploads resume; `ResumeParser` extracts text; `local_interview_model.extract_resume_profile` identifies 15 profile attributes.
   - Session created via `POST /api/interview/session/create`; countdown deadline timestamp calculated and locked.

2. **Phase 1: Self-Introduction:**
   - The engine generates a single self-introduction prompt welcoming the candidate and referencing their primary domain.
   - Candidate responds via microphone (streamed in 16 kHz WAV chunks to ASR sidecar) or text input.
   - System evaluates initial communication clarity and relevance.

3. **Phase 2: General Role Competencies:**
   - The engine asks general behavioral/engineering fit questions (motivation, teamwork, task prioritization).
   - Expected points are generated internally but strictly suppressed from candidate API responses.

4. **Phase 3: Role-Specific Technical Questions & Adaptive Follow-Ups:**
   - The engine presents main technical questions aligned with the candidate's selected role and difficulty.
   - For each candidate answer:
     - If candidate indicates unfamiliarity ("I don't know", "skip"), a single clarification scaffolding prompt is offered; if repeated, the engine moves immediately to `next_topic`.
     - If candidate gives a brief or partial answer, the engine formulates a targeted probe referencing a missing engineering trade-off or architectural constraint.
     - **Follow-up Turn Limit:** A maximum of 2 follow-ups are permitted per topic group. The `followups_used` counter is strictly reset to 0 *only* when transitioning to a new main topic via `next_topic`.
     - If session duration expires, the turn policy issues `action: "end"` regardless of remaining topics.

5. **Phase 4: Session Completion, Rubric Evaluation, and Storage:**
   - Audio tracks are halted; `POST /api/rubric/assess` groups turns into `TopicGroup` objects.
   - Scoring anchors (0–4) are evaluated with candidate quote verification.
   - Equal group-weighted aggregation computes earned marks across assessed criteria.
   - Non-scoring coaching observations (emotions, gaze, eye contact %) are appended outside the 100 marks.
   - Final JSON payload is stored in `backend/data/reports/${sessionId}.json` and cached in browser storage.

---

## 4. MODEL AND DATASET DETAILS

### 4.1 Machine Learning Models

#### Model M1: Facial Emotion Classifier (MobileNetV2 Transfer Learning)
- **Algorithm & Backbone:** MobileNetV2 pretrained on ImageNet, fine-tuned on FER-2013 with classification head (`GlobalAveragePooling2D` $\rightarrow$ `Dense(256, relu)` $\rightarrow$ `Dropout(0.4)` $\rightarrow$ `Dense(7, softmax)`).
- **Source Code:** [`ml/emotion_v2/train_v2.py`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py)
- **Input Format:** $96 \times 96 \times 3$ RGB images normalized to $[0.0, 1.0]$.
- **Output Format:** 7-class probability vector (`angry`, `disgust`, `fear`, `happy`, `neutral`, `sad`, `surprise`).
- **Training Hyperparameters:** Optimizer: Adam ($\text{lr} = 1\times 10^{-4}$); Loss: Categorical Cross-Entropy; Batch Size: 64; Epochs: 50 with Early Stopping ($\text{patience} = 7$); Data Augmentation: Random rotation ($\pm 15^\circ$), width/height shift ($\pm 10\%$), horizontal flip.
- **Model Checkpoint Artifact:** `emotion_model_v2.keras` (Size: 27.26 MB; weights stored externally, eval metrics local).

#### Model M2: Gaze & Eye-Contact Regressor (Custom CNN)
- **Algorithm:** 3-block Convolutional Neural Network with Batch Normalization:
  - Block 1: `Conv2D(32, 3x3, relu)` $\rightarrow$ `BatchNorm` $\rightarrow$ `MaxPool2D(2x2)`
  - Block 2: `Conv2D(64, 3x3, relu)` $\rightarrow$ `BatchNorm` $\rightarrow$ `MaxPool2D(2x2)`
  - Block 3: `Conv2D(128, 3x3, relu)` $\rightarrow$ `BatchNorm` $\rightarrow$ `MaxPool2D(2x2)`
  - Head: `Flatten` $\rightarrow$ `Dense(256, relu)` $\rightarrow$ `Dropout(0.4)` $\rightarrow$ `Dense(128, relu)` $\rightarrow$ `Dropout(0.3)` $\rightarrow$ `Dense(2, linear)` (Pitch, Yaw).
- **Source Code:** [`ml/eye_contact/train.py`](file:///d:/nishanth_work/final_project/ml/eye_contact/train.py#L27-L52)
- **Input Format:** Right-eye image crop isolated via MediaPipe 468-point FaceMesh landmarks.
- **Output Format:** 2 continuous float values representing pitch and yaw in radians.
- **Calibrated Eye-Contact Boundary:**
  - Center: $\text{pitch} = -0.15278$, $\text{yaw} = -0.07262$
  - Tolerances: $\Delta \text{pitch} \le 0.060$, $\Delta \text{yaw} \le 0.075$
  - Candidate is labeled `looking_at_camera = True` if and only if both offsets fall within these tolerances.

#### Model M3: Fine-Tuned Whisper ASR (LoRA Adapter)
- **Algorithm & Backbone:** `openai/whisper-base.en` with Low-Rank Adaptation (LoRA) via HuggingFace PEFT.
- **Quantization:** 8-bit quantized backbone via `BitsAndBytesConfig(load_in_8bit=True)` to enable execution within constrained VRAM (< 4 GB).
- **LoRA Parameters:** Rank $r = 8$, $\alpha = 16$, Target Modules: `["q_proj", "v_proj"]`, Dropout: 0.05, Trainable Bias: `none`.
- **Source Code:** [`ml/asr_training/train_full.py`](file:///d:/nishanth_work/final_project/ml/asr_training/train_full.py#L80-L97)
- **Input Format:** 16 kHz 1D audio waveform transformed to 80-channel log-mel spectrogram features.
- **Output Format:** Autoregressive token generation decoded into English orthographic text.

#### Model M4: Local Interview Language & Rubric Engine
- **Algorithm:** Deterministic taxonomy matching, structural STAR stage recognition, and token-level Jaccard similarity.
- **Source Code:** [`backend/app/services/local_interview_model.py`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py), [`backend/app/rubric/evaluator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py)
- **Operation:** Evaluates technical mechanism counts, boundary distinctions, and verifiable quotation substrings without stochastic hallucinations.

---

### 4.2 Datasets and Data Governance

#### Dataset D1: PreMock Multi-Task Interview Dataset (`interview_dataset.csv`)
- **Location:** [`backend/data/interview_dataset.csv`](file:///d:/nishanth_work/final_project/backend/data/interview_dataset.csv)
- **Sample Count:** Exactly 10,000 samples across 17 structured columns.
- **Task Distribution:**
  - `resume_extract`: 4,875 records (48.75%)
  - `role_question`: 2,565 records (25.65%)
  - `followup`: 2,560 records (25.60%)
- **Split Distribution:**
  - `train`: 8,000 records (80.0%)
  - `validation`: 1,129 records (11.29%)
  - `test`: 871 records (8.71%)
- **Data Provenance and Licenses:**
  - `original_synthetic_scenario_templates`: 4,915 records, CC0-1.0 Universal license.
  - `publisher_declared_synthetic_llm_labeled`: 4,875 records, adapted from HuggingFace dataset `sandeeppanem/resume-json-extraction-5k`, Apache-2.0 license.
  - `public_source_adapted`: 210 records, CC-BY-4.0 license.
- **Role Coverage:** 2,912 distinct job roles represented.
- **Exported Formats:** Chat-formatted JSONL splits exported in [`backend/data/finetuning/`](file:///d:/nishanth_work/final_project/backend/data/finetuning/) (`train_all.jsonl` [56.98 MB], `train_questions.jsonl` [6.35 MB], `train_followups.jsonl` [8.87 MB]).

#### Dataset D2: FER-2013 (Facial Expression Recognition)
- **Documented Source:** Kaggle / ICML 2013 Challenges in Representation Learning.
- **License:** Open academic research use.
- **Sample Count:** 35,887 images total across 7 classes (`angry`, `disgust`, `fear`, `happy`, `neutral`, `sad`, `surprise`).
- **Held-Out Test Set:** Exactly 7,178 images evaluated in [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json#L62).
- **Leakage Prevention:** Standard fixed test set benchmark; no training images overlap into validation/test splits.

#### Dataset D3: MPIIGaze
- **Documented Source:** Max Planck Institute for Informatics (MPII).
- **License:** Non-commercial academic research license.
- **Sample Count:** 213,659 images collected from 15 participants in natural daily laptop usage.
- **Preprocessing:** Face crop, right-eye alignment via MediaPipe FaceMesh, pitch/yaw offset normalization.

#### Dataset D4: Common Voice Indian English Accent (`ishands/commonvoice-indian_accent`)
- **Documented Source:** HuggingFace Hub: `ishands/commonvoice-indian_accent` (derived from Mozilla Common Voice).
- **License:** CC0-1.0 / Mozilla Public License.
- **Sample Count:** 110,088 recordings.
- **Speaker Separation & Leakage Verification:**
  - Strict speaker-disjoint splitting documented in [`ml/asr_training/full_speaker_split.json`](file:///d:/nishanth_work/final_project/ml/asr_training/full_speaker_split.json) and [`ml/asr_training/fix_speaker_split.py`](file:///d:/nishanth_work/final_project/ml/asr_training/fix_speaker_split.py).
  - All recordings grouped by `client_id`; 100% of samples for a given speaker are assigned exclusively to either `train`, `validation`, or `test`. Zero speaker overlap across splits.

---

## 5. SCORING METHODOLOGY

### 5.1 Rubric Specification (`interview_practice_100_v1`)

The platform implements an objective 100-mark assessment rubric codified in [`backend/app/rubric/config.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py):

$$\sum_{i=1}^{7} \text{MaxMarks}_i = 30.0 + 20.0 + 15.0 + 10.0 + 10.0 + 10.0 + 5.0 = 100.0$$

| Criterion ID | Criterion Name | Max Marks | Integer Anchors (0 to 4) | Eligibility Profile |
| :--- | :--- | :---: | :--- | :--- |
| `technical_knowledge` | Technical / Job-Role Knowledge | **30.0** | **0:** Misconception / no substantive explanation.<br>**1:** Recognizes terms with major errors.<br>**2:** Partly correct with important gaps.<br>**3:** Correct concepts & mechanisms for level.<br>**4:** Accurate distinctions, boundaries & counterexamples. | Technical questions |
| `problem_solving` | Problem-Solving & Reasoning | **20.0** | **0:** No workable approach presented.<br>**1:** Guesses without logical justification.<br>**2:** Plausible approach with verification gaps.<br>**3:** Coherent steps, justified decisions.<br>**4:** Compares alternatives, explains trade-offs, verifies failure cases. | Technical, Practical, Soft Skill |
| `practical_application` | Practical Application & Examples | **15.0** | **0:** No usable example.<br>**1:** Generic claims without concrete actions.<br>**2:** Relevant example with unclear outcomes.<br>**3:** Concrete actions, plausible outcomes.<br>**4:** Specific decisions, checks, limitations (accepts coursework/projects). | Technical, Practical, Soft Skill |
| `relevance_completeness` | Relevance & Completeness | **10.0** | **0:** Does not address question.<br>**1:** Addresses peripheral points.<br>**2:** Addresses main request, misses key parts.<br>**3:** Covers important requested components.<br>**4:** Complete, focused, prioritized response. | All interview phases |
| `communication_clarity` | Communication Clarity | **10.0** | **0:** Uninterpretable with usable evidence.<br>**1:** Disconnected ideas.<br>**2:** Understandable main point, organizational gaps.<br>**3:** Clear organization & precision.<br>**4:** Precise explanation with definitions & transitions. | All interview phases |
| `followup_reflection` | Follow-Up Response & Reflection | **10.0** | **0:** Does not engage with probe.<br>**1:** Repeats original answer without depth.<br>**2:** Addresses part of the probe.<br>**3:** Clarifies or corrects reasoning under probe.<br>**4:** Coherently incorporates probe, supports with trade-offs. | Follow-up turns only |
| `spoken_delivery` | Spoken Delivery & Intelligibility | **5.0** | **0:** Unintelligible despite usable recording.<br>**1:** Frequently obscures meaning.<br>**2:** Understandable with recurring interference.<br>**3:** Understandable pacing & audibility.<br>**4:** Consistently easy to follow with useful pauses. | Audio evidence / Human review |

### 5.2 Deterministic Aggregation Formula

1. **Topic Grouping:** Turns are grouped into cohesive `TopicGroup` structures. A main question and up to two subsequent follow-up probes form a single topic group.
2. **Equal Group Weighting:** The rating for criterion $c$ is averaged equally across all eligible topic groups:
   $$\text{Rating}(c) = \frac{1}{|G_{\text{eligible}}(c)|} \sum_{g \in G_{\text{eligible}}(c)} \text{Rating}_g(c)$$
   *Critical Invariant:* Having two follow-up probes in Topic A and zero follow-up probes in Topic B does *not* give Topic A triple the weight. Both topics contribute equally (50% each) to shared criteria.
3. **Earned Marks Calculation:**
   $$\text{EarnedMarks}(c) = \frac{\text{Rating}(c)}{4.0} \times \text{MaxMarks}(c)$$

### 5.3 Handling Missing Signals, Evasions, and Vision Data

- **Missing Audio Delivery Signal:** When audio evidence is absent or unreviewed, `spoken_delivery` is set to `None`. The engine sets:
  - `assessment_status = "partial"`
  - `assessed_maximum = 95.0`
  - `total_score_100 = None` (strictly avoiding misrepresenting a 95-mark assessment as a 100-mark assessment)
  - `provisional_normalized_100 = (assessed_score / 95.0) * 100`
  - `coverage_percent = 95.0%`
- **Candidate Non-Answers and Evasions:** Explicit non-answers ("I don't know", "skip", "no idea", empty input) are assigned Anchor 0 (0.0 rating) across eligible criteria, earning 0 marks.
- **Multimodal Separation:** Facial emotion distributions, gaze pitch/yaw, and eye contact percentage are strictly restricted to `coaching_observations`. They have exactly **0% mathematical weight** on the 100-mark score.
- **Proctoring Penalties:** Candidate window switching or full-screen exit violations apply an objective penalty of -4 marks per violation (capped at -16 marks) directly to the proctoring score.

---

## 6. VERIFIED EXPERIMENTS AND RESULTS

### 6.1 Verified Facial Emotion Transfer Learning Experiment

Experimental results extracted directly from [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json) and [`training_history_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/training_history_v2.json):

- **Model Checkpoint:** `emotion_model_v2.keras`
- **Backbone:** MobileNetV2 (ImageNet pretrained transfer learning)
- **Input Resolution:** $96 \times 96 \times 3$ RGB
- **Benchmark Test Set:** FER-2013 held-out test split ($N = 7,178$ test images)
- **Measured Metrics:**
  - **Overall Test Accuracy:** **63.96%** (4,591 / 7,178 correct)
  - **Macro F1-Score:** **62.48%**
  - **Weighted F1-Score:** **63.89%**
  - **Macro Precision:** 62.54%
  - **Macro Recall:** 62.78%
  - **Best Validation Accuracy:** **64.47%**
  - **Baseline Comparison:** Prior v1 baseline achieved 61.72%. Measured fine-tuning improvement: **+2.24 percentage points**.
  - **Training Duration:** 8,241.6 seconds (~2.29 hours)
  - **Model File Size:** 27.26 MB

#### Class-Wise Performance Breakdown (FER-2013 Test Set, $N = 7,178$)

| Emotion Class | Precision | Recall | F1-Score | Test Support |
| :--- | :---: | :---: | :---: | :---: |
| **Happy** | **85.89%** | **82.02%** | **83.91%** | 1,774 |
| **Surprise** | **73.22%** | **80.63%** | **76.75%** | 831 |
| **Disgust** | 62.28% | 63.96% | 63.11% | 111 |
| **Neutral** | 55.80% | 60.83% | 58.21% | 1,233 |
| **Angry** | 56.03% | 53.34% | 54.65% | 958 |
| **Sad** | 49.61% | 55.49% | 52.38% | 1,247 |
| **Fear** | 54.98% | 43.16% | 48.36% | 1,024 |
| **Macro Average** | **62.54%** | **62.78%** | **62.48%** | 7,178 |
| **Weighted Average** | **64.19%** | **63.96%** | **63.89%** | 7,178 |

#### Confusion Matrix ($7 \times 7$ Test Predictions)
```
            Angry  Disgust   Fear   Happy  Neutral    Sad  Surprise
Angry   [    511,      20,    79,     38,     107,   161,       42 ]
Disgust [     18,      71,     3,      4,       3,    11,        1 ]
Fear    [    123,       7,   442,     27,     113,   209,      103 ]
Happy   [     65,       4,    39,   1455,     115,    57,       39 ]
Neutral [     61,       4,    62,     85,     750,   241,       30 ]
Sad     [    112,       5,   125,     53,     230,   692,       30 ]
Surprise[     22,       3,    54,     32,      26,    24,      670 ]
```

### 6.2 Verified Rubric Unit Test Suite Results

Test execution verified via [`backend/tests/test_rubric_100.py`](file:///d:/nishanth_work/final_project/backend/tests/test_rubric_100.py):
- **Command:** `python -m unittest tests/test_rubric_100.py`
- **Result:** **10 tests passed in 0.018 seconds (100% pass rate)**.
- **Verified Invariants:**
  1. All ratings 4.0 strictly yield $100.0 / 100.0$ ($100\%$ coverage, `status: "complete"`).
  2. All ratings 0.0 strictly yield $0.0 / 100.0$ ($100\%$ coverage, `status: "complete"`).
  3. Ratings $[3, 3, 3, 4, 3, 2, 3]$ strictly evaluate to $75.00 / 100.0$.
  4. Missing spoken delivery produces $\text{assessed\_maximum} = 95.0$, `total_score_100 = None`, and `status = "partial"`.
  5. All null ratings produce `total_score_100 = None` and `status = "unassessed"`.
  6. Rejection of booleans (`True/False`), NaN, Infinity, negative values, and numbers $> 4.0$.
  7. Detection of fabricated quotations not present in candidate answer transcripts.
  8. Extra follow-up turns do not multiply topic weight.
  9. Vision coaching metrics (emotion, eye-contact) do not alter rubric scores.

### 6.3 Pilot ASR Training Log Discrepancy Evidence

Documented in [`ml/asr_training/inspect_training_loss.py`](file:///d:/nishanth_work/final_project/ml/asr_training/inspect_training_loss.py#L72-L106):
- In early pilot training on 100 samples across 50 steps, training loss was logged at 15.70, while evaluation loss on the validation subset logged at 3.48.
- Analysis confirms both compute cross-entropy, but training loss reflected per-batch variance under 8-bit quantization noise, whereas evaluation loss operated in float16 inference mode.
- *Reporting Guardrail:* The full dataset training on 20,000 / 110,088 samples was structured across scripts (`train_20k.py`, `train_full.py`), but execution checkpoints were not written to this local workspace. Therefore, no unverified WER percentage is asserted as a completed local result.

### 6.4 Proposed Evaluation Plan for Unmeasured Modules

For components lacking complete local test logs, the following rigorous evaluation methodology is established:

```
+----------------------------------------------------------------------------------------------------+
|                                PROPOSED EVALUATION PLAN FOR UNMEASURED MODULES                     |
+----------------------+-----------------------------+-----------------------+-----------------------+
| Module               | Evaluation Benchmark        | Metric Definitions    | Sample Size & Setup   |
+----------------------+-----------------------------+-----------------------+-----------------------+
| Speech-to-Text (ASR) | Common Voice Indian Accent  | Word Error Rate (WER) | 500 held-out speakers |
|                      | held-out test split         | Char Error Rate (CER) | strictly disjoint     |
| Gaze Estimation      | MPIIGaze test partition     | Mean Angular Error (°) | 15 cross-subject test |
|                      |                             | Looking-at-cam Prec/Rec| sessions              |
| Rubric Reliability   | 50 mock interview sessions  | Cohen's Kappa (κ),    | 3 independent expert  |
|                      | with diverse responses      | Pearson/Spearman (r)  | human software review |
+----------------------+-----------------------------+-----------------------+-----------------------+
```

---

## 7. INTEGRATION WITH THE OTHER WORKSPACE

### 7.1 Architecture Division of Responsibilities

| Subsystem Component | Present in THIS Workspace (`MY_PART`) | Expected from OTHER Workspace (`FRIEND_PART`) |
| :--- | :---: | :---: |
| **Next.js 16 Web Application & UI** | **Present (Complete)** | Client components or alternative dashboard |
| **FastAPI Core Backend & Routes** | **Present (Complete)** | Alternative backend or external service integrations |
| **Resume Extraction & Taxonomy Plan** | **Present (Complete)** | Parsing enhancements or alternative OCR |
| **Session Lifecycle State Machine** | **Present (Complete)** | Session sync or database adapters |
| **100-Mark Rubric Evaluator Engine** | **Present (Complete)** | Evaluation validation / human review scoring |
| **MobileNetV2 FER-2013 Pipeline** | **Present (Complete)** | Checkpoint hosting or alternative models |
| **MPIIGaze Regressor Calibration** | **Present (Complete)** | Checkpoint hosting or real-time landmark pipeline |
| **Whisper LoRA Training Pipeline** | **Present (Complete)** | High-GPU ASR checkpoint hosting |
| **Posture Analysis Vision Model** | **Missing (Placeholder)** | **Expected to be provided by FRIEND_PART** |
| **Acoustic Voice / Prosody DSP Model** | **Missing (Placeholder)** | **Expected to be provided by FRIEND_PART** |
| **Cloud GPU Checkpoint Serving** | **Missing (Local code only)** | Hosted microservice endpoints for `.keras` / `.pt` |

### 7.2 API Contracts and Integration Interfaces

#### 1. Turn Submission Endpoint (`POST /api/interview/session/{session_id}/submit-turn`)
- **Request Payload:**
  ```json
  {
    "answer": "We implemented optimistic concurrency using database version columns.",
    "turn_id": "turn_3_1710000000",
    "next_main_difficulty": null
  }
  ```
- **Response Schema (`TurnSubmitResponse`):**
  ```json
  {
    "action": "follow_up",
    "next_question": {
      "question": "How did you handle rollback and user notification when concurrent update conflicts occurred?",
      "topic": "Database transactions and query optimization",
      "kind": "follow_up",
      "difficulty": "intermediate"
    },
    "session_id": "uuid-v4",
    "turn_index": 3,
    "current_topic_index": 1,
    "followups_used": 1,
    "remaining_topics_count": 4,
    "is_complete": false,
    "deadline_expired": false,
    "evaluation": {
      "score": 75,
      "relevance": 80,
      "technical_depth": 70,
      "clarity": 75,
      "completeness": 65
    }
  }
  ```

#### 2. Rubric Assessment Endpoint (`POST /api/rubric/assess`)
- **Request Payload (`RubricAssessSessionRequest`):**
  ```json
  {
    "session_id": "uuid-v4",
    "job_role": "Backend Engineer",
    "difficulty": "intermediate",
    "turns": [
      {
        "turn_index": 1,
        "question": "Explain database indexing mechanisms.",
        "answer": "B-Tree indexes provide O(log n) lookups. We added composite indexes to speed up read queries.",
        "phase": "technical",
        "is_followup": false,
        "audio_present": true
      }
    ],
    "spoken_delivery_rating": null,
    "coaching_observations": {
      "facial_expressions": { "neutral": 70, "happy": 30 },
      "eye_contact_percent": 82.5,
      "face_present_percent": 98.0,
      "posture": null
    }
  }
  ```
- **Response Schema (`RubricAssessmentResponse`):**
  ```json
  {
    "rubric_version": "interview_practice_100_v1",
    "job_role": "Backend Engineer",
    "difficulty": "intermediate",
    "assessment_status": "partial",
    "total_score_100": null,
    "provisional_normalized_100": 78.95,
    "assessed_score": 75.0,
    "assessed_maximum": 95.0,
    "coverage_percent": 95.0,
    "missing_criteria": ["spoken_delivery"],
    "criteria": {
      "technical_knowledge": {
        "criterion_id": "technical_knowledge",
        "name": "Technical / job-role knowledge",
        "rating": 3.0,
        "maximum_marks": 30.0,
        "earned_marks": 22.5,
        "is_assessed": true,
        "reason": "Topic 1: Anchor 3: Correct concepts and mechanisms for the selected level.",
        "evidence": [
          { "quote": "B-Tree indexes provide O(log n) lookups", "verified": true, "group_id": "topic_1" }
        ]
      }
    },
    "topic_groups": [...],
    "coaching_observations": {
      "note": "Optional audiovisual feedback for practice coaching only. Does NOT impact the 100-mark assessment.",
      "eye_contact_percent": 82.5,
      "face_present_percent": 98.0
    }
  }
  ```

#### 3. Vision Inference Microservice Contract (`POST http://127.0.0.1:8000/api/emotion/predict`)
- **Request:** `multipart/form-data` with `file: <binary_jpeg_webcam_frame>`.
- **Response Schema (`EmotionResponse`):**
  ```json
  {
    "emotion": "neutral",
    "confidence": 0.824,
    "face_present": true,
    "face_count": 1,
    "looking_at_camera": true,
    "gaze_pitch": -0.148,
    "gaze_yaw": -0.069,
    "error": null,
    "gaze_error": null
  }
  ```

### 7.3 Integration Gaps and Potential Overlaps
1. **Model Weights Location:** This workspace contains all source code, unit tests, schemas, and dataset splits, but `.keras` and `.pt` weight binaries are not committed locally. The combined system must configure `MODEL_PATH` environment variables pointing to shared weight volumes or GPU endpoints.
2. **Missing Posture and Prosody Implementations:** Posture analysis and acoustic prosody models are unrepresented in this workspace. If `FRIEND_PART` implements these modules, they must plug directly into `coaching_observations["posture"]` and `spoken_delivery_rating` in the rubric engine.
3. **Audio Format Compatibility:** `ml/asr_service/asr_server.py` rejects `audio/webm` with HTTP 415 unless FFmpeg is installed to decode WebM into WAV. The combined pipeline must standardize on client-side WAV encoding (as currently implemented in `frontend/src/app/interview/[id]/page.tsx`) or deploy server-side FFmpeg transcoding.

---

## 8. RESEARCH-PAPER EVIDENCE AND LIMITATIONS

### 8.1 Methodological Contributions for the Paper
1. **Deterministic 100-Mark Rubric Engine with Integer Anchors:** Unlike black-box LLM scoring prompts, PreMock AI implements a transparent, versioned rubric (`interview_practice_100_v1`) with integer rating anchors (0–4) across 7 criteria.
2. **Verifiable Quotation Grounding:** All rubric ratings require verifiable textual evidence extracted directly from candidate answers. An exact-substring verifier flags any hallucinated quotations with `review_status = "requires_review"`.
3. **Equal Topic-Group Aggregation:** Proves mathematically and experimentally that variable follow-up turn counts do not skew criterion weights across topics.
4. **Fair Multimodal Separation:** Formulates an ethical boundary isolating non-scoring vision metrics (facial expressions, eye contact) from technical competencies, eliminating bias against candidates with neurodivergent eye-contact traits or webcam limitations.
5. **Speaker-Disjoint ASR Partitioning:** Establishes speaker-safe dataset splits for Indian English accent adaptation, preventing speaker identity leakage between training and testing sets.

### 8.2 Citation Index for Implementation Claims

Every core system capability is directly verified in the codebase:

- **100-Mark Rubric Weights & Anchors:** [`backend/app/rubric/config.py::RUBRIC_CRITERIA`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py#L10-L102)
- **Deterministic Math Engine:** [`backend/app/rubric/calculator.py::compute_rubric_assessment`](file:///d:/nishanth_work/final_project/backend/app/rubric/calculator.py#L74-L165)
- **Equal Group Aggregator:** [`backend/app/rubric/aggregator.py::aggregate_criterion_ratings_across_groups`](file:///d:/nishanth_work/final_project/backend/app/rubric/aggregator.py#L110-L142)
- **Quote Verifier & Concept Catalog:** [`backend/app/rubric/evaluator.py::verify_evidence_quote`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L162-L172)
- **Rubric Unit Test Suite:** [`backend/tests/test_rubric_100.py`](file:///d:/nishanth_work/final_project/backend/tests/test_rubric_100.py)
- **Role Taxonomies & Follow-Up Policies:** [`backend/app/services/local_interview_model.py::ROLE_TAXONOMIES`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L28-L600)
- **Private `expected_points` Filter:** [`backend/app/services/session_manager.py::get_candidate_session_view`](file:///d:/nishanth_work/final_project/backend/app/services/session_manager.py#L328-L376)
- **Resume 15-Field Profile Extractor:** [`backend/app/services/local_interview_model.py::extract_resume_profile`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L600-L728)
- **MobileNetV2 FER-2013 Training Script:** [`ml/emotion_v2/train_v2.py`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py)
- **FER-2013 Measured Test Report:** [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json)
- **Gaze Thresholds Calibration:** [`ml/eye_contact/eye_contact_thresholds.json`](file:///d:/nishanth_work/final_project/ml/eye_contact/eye_contact_thresholds.json)
- **Speaker-Safe ASR Dataset Split:** [`ml/asr_training/full_speaker_split.json`](file:///d:/nishanth_work/final_project/ml/asr_training/full_speaker_split.json)
- **Multi-Task Dataset Metadata:** [`backend/data/interview_dataset.csv`](file:///d:/nishanth_work/final_project/backend/data/interview_dataset.csv)
- **Human Review Override Route:** [`backend/app/routes/rubric.py::manual_criterion_override`](file:///d:/nishanth_work/final_project/backend/app/routes/rubric.py#L65-L129)
- **Full Report Disk Persistence:** [`backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json`](file:///d:/nishanth_work/final_project/backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json)

### 8.3 Documented Limitations
1. **Absence of Local Checkpoint Weights:** Large deep learning weight files (`.keras` and `.pt`) were omitted from local repository tracking; microservices require external weights to execute live inferences.
2. **Missing Posture & Prosody Signals:** The platform handles missing posture and prosody signals gracefully in software, but lacks functional machine learning models for these modalities in this workspace.
3. **Lexical vs. Semantic Paraphrase Sensitivity:** While the concept catalog encompasses 200+ normalized mechanisms, candidates describing advanced concepts using idiosyncratic non-standard terminology may receive lower automated anchor ratings unless reviewed by a human evaluator.
4. **Browser Audio Constraint:** Real-time ASR requires client-side WAV encoding or local FFmpeg binaries, as WebM audio streams cannot be parsed natively by `soundfile`.

---

## 9. COMPACT SUMMARY TABLE

| Module | Status | Method / Model | Evidence File & Entry | Measured Result | Missing Details / Gaps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Resume Extraction & Job-Role Selection** | **Completed** | PyPDF2 text parser + local regex profile extractor | [`backend/app/routes/resume.py`](file:///d:/nishanth_work/final_project/backend/app/routes/resume.py#L20-L68), [`backend/app/services/local_interview_model.py`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L600-L728) | Extracts 15 structured fields reliably; maps to 6 canonical taxonomies | Scanned OCR without text layer requires Tesseract fallback |
| **Question Generation & Follow-ups** | **Completed** | Phased session state machine + local token deduplication | [`backend/app/services/session_manager.py`](file:///d:/nishanth_work/final_project/backend/app/services/session_manager.py#L70-L325), [`backend/app/services/local_interview_model.py`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py#L1144-L1285) | Intro $\rightarrow$ General $\rightarrow$ Technical flow; max 2 follow-ups enforced | Subjective naturalness requires human user study |
| **Speech-to-Text (ASR)** | **Partial** | Fine-tuned `whisper-base.en` + LoRA ($r=8$, $\alpha=16$) | [`ml/asr_service/asr_server.py`](file:///d:/nishanth_work/final_project/ml/asr_service/asr_server.py), [`ml/asr_training/full_speaker_split.json`](file:///d:/nishanth_work/final_project/ml/asr_training/full_speaker_split.json) | Pilot training logged train loss = 15.70, eval loss = 3.48 | LoRA checkpoint weights missing locally; WebM requires FFmpeg |
| **Facial Expression Analysis** | **Completed (Model) / Partial (Runtime)** | MobileNetV2 transfer learning on FER-2013 | [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json), [`ml/emotion_v2/train_v2.py`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py) | **Test Acc: 63.96%, Macro F1: 62.48%** on 7,178 test images (+2.24 pp over baseline) | Checkpoint binary `emotion_model_v2.keras` external to repo |
| **Gaze / Eye-Contact Estimation** | **Completed (Calib) / Partial (Runtime)** | MediaPipe FaceMesh (468 landmarks) + CNN regressor on MPIIGaze | [`ml/eye_contact/eye_contact_thresholds.json`](file:///d:/nishanth_work/final_project/ml/eye_contact/eye_contact_thresholds.json), [`backend/app/services/gaze_service.py`](file:///d:/nishanth_work/final_project/backend/app/services/gaze_service.py) | Calibrated center pitch (-0.1528) and yaw (-0.0726) thresholds | Gaze model `.keras` binary external to repo |
| **Posture Analysis** | **Placeholder** | None (Schema placeholder) | [`backend/app/rubric/schemas.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/schemas.py), [`frontend/src/app/interview/[id]/page.tsx`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/%5Bid%5D/page.tsx#L743) | Returns `posture: null` without affecting marks | No model or landmark pipeline implemented |
| **Voice / Prosody Analysis** | **Rule-Based Fallback** | Filler-word ratio + manual human review override | [`backend/app/rubric/evaluator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L449-L483), [`backend/app/routes/rubric.py`](file:///d:/nishanth_work/final_project/backend/app/routes/rubric.py#L65-L129) | Evaluated over usable audio or via manual review API | Acoustic DSP features (pitch, jitter, shimmer) not implemented |
| **Answer / Content Scoring** | **Completed** | Deterministic concept catalog (200+ entities) + STAR matcher | [`backend/app/rubric/evaluator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L196-L423) | Proposes ratings 0–4 with verified candidate quote fragments | Lexical matching may miss rare colloquial phrasing |
| **Score Aggregation** | **Completed** | Equal group-weighted arithmetic average across topic groups | [`backend/app/rubric/aggregator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/aggregator.py#L110-L142), [`backend/app/rubric/calculator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/calculator.py#L74-L165) | 10/10 unit tests pass (0.018s); follow-ups do not inflate topic weights | Fully implemented and mathematically verified |
| **Feedback & Report Generation** | **Completed** | Provenance report generator + disk JSON persistence | [`backend/app/routes/reports.py`](file:///d:/nishanth_work/final_project/backend/app/routes/reports.py#L64-L95), [`backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json`](file:///d:/nishanth_work/final_project/backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json) | Reports persistently saved to disk; manual review & CSV export functional | PDF download format planned |
