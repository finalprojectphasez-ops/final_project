# Research Evidence and Audit Report (Workspace: MY_PART)

**Project Title:** AI-Powered Video Interview Practice Platform with Automated Performance Evaluation and Personalized Feedback Reports (PreMock AI)  
**Workspace Identifier:** `MY_PART`  
**Audit Completed:** October 2026 (Verified against workspace filesystem and Git commit state)  
**Repository Commit Hash:** `b5e261ede09a125d060dd4faae22eaf5632c9254`  
**Target Path:** `d:/nishanth_work/final_project/research_evidence_MY_PART.md`  

---

## 1. FINAL IMPLEMENTATION AUDIT

### 1.1 Active Question Engine: Local vs. OpenRouter
- **Active Operational Engine:** **Strictly Local Language Model Service (`local_interview_model.py`)**.
  - All live API routes in [`backend/app/routes/interview.py`](file:///d:/nishanth_work/final_project/backend/app/routes/interview.py#L22-L23) explicitly import and route turn requests through:
    - `from app.services.session_manager import session_manager`
    - `from app.services.local_interview_model import local_interview_model, normalize_role, normalize_difficulty`
  - Active question generation endpoints (`/api/interview/session/create`, `/api/interview/session/{id}/submit-turn`, `/api/interview/next-turn`, `/api/interview/generate-question`) execute 100% locally via deterministic taxonomies, STAR pattern extractors, and token Jaccard similarity.
- **Status of OpenRouter:** **Unreferenced / Orphaned Legacy Fallback**.
  - While [`backend/app/config.py`](file:///d:/nishanth_work/final_project/backend/app/config.py#L16-L19) defines environment variables (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"`, `OPENAI_API_KEY`, `GROQ_API_KEY`), and an implementation exists in [`backend/app/services/interview_llm_service.py`](file:///d:/nishanth_work/final_project/backend/app/services/interview_llm_service.py), this class is **nowhere imported or mounted** in `backend/app/main.py` or any active route file.
  - The running system operates completely offline without dispatching remote HTTP requests to OpenRouter.

### 1.2 Active Rubric and Aggregation Engine
- **Active Production Rubric:** `interview_practice_100_v1` defined in [`backend/app/rubric/config.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py#L8-L102).
- **Active Aggregation Method:** **Equal Topic-Group Weighted Arithmetic Mean** (`backend/app/rubric/aggregator.py::aggregate_criterion_ratings_across_groups`). Turns are grouped into `TopicGroup` objects; follow-up probes do not inflate topic weights.
- **Mathematical Calculator:** Full precision internal float evaluation rounded to 2 decimal places in [`backend/app/rubric/calculator.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/calculator.py#L74-L165).

### 1.3 Persistence Architecture
- **Primary Persistent System:** **Local Filesystem JSON Storage**.
  - Sessions: `backend/data/sessions/{session_id}.json` managed by `SessionManager` (`backend/app/services/session_manager.py`).
  - Reports: `backend/data/reports/{session_id}.json` managed by `reports.py` (`backend/app/routes/reports.py`).
- **Client Caching:** Browser `sessionStorage` (`report_{sessionId}`, `premock_session_history`).
- **Cloud Database (Supabase):** Optional sync wrapped in non-blocking try/catch blocks in `frontend/src/app/interview/[id]/page.tsx:L810-L825`. If unconfigured, the app runs entirely on local disk.

### 1.4 Service Topology and Ports
- **Port 8000:** Core PreMock FastAPI Engine (`backend/app/main.py`).
- **Port 8001:** MPIIGaze Inference Server (`backend/gaze_service_server.py`).
- **Port 8002:** MobileNetV2 Emotion Inference Server (`backend/emotion_service_server.py`).
- **Port 8003:** Whisper ASR Sidecar (`ml/asr_service/asr_server.py`).
- **Port 3000 / 3001:** Next.js 16 Frontend Web Application (`frontend/`).

### 1.5 Separation of Functioning Services vs. Missing Checkpoints
- **Fully Functioning End-to-End:**
  - Setup, Resume Ingestion, Phased Session Flow (Intro $\rightarrow$ General $\rightarrow$ Technical $\rightarrow$ Closing).
  - 100-Mark Rubric Evaluation, Quotation Verifier, Topic Aggregation, Report Persistence, Manual Review Overrides, CSV/JSON Exports.
- **Functioning Code with Missing Binary Checkpoints in Workspace:**
  - `backend/emotion_service_server.py`: Server script is complete, but `backend/ml_models/emotion_model.keras` is absent from this repository workspace (evaluation metrics and training history are preserved in `ml/emotion_v2/outputs/`).
  - `backend/gaze_service_server.py`: Server script and calibration configuration exist, but `backend/ml_models/gaze_model.keras` is absent.
  - `ml/asr_service/asr_server.py`: Server script and audio processing exist, but `ml/asr_model/whisper_indian_accent_lora_20k` is absent.

---

## 2. COMPLETE RUBRIC SPECIFICATION & AUDIT OF THE 110-POINT ANOMALY

### 2.1 The Official Production Rubric (`interview_practice_100_v1`)
Documented in [`backend/app/rubric/config.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py#L10-L106):
Total Maximum Marks: Exactly **100.0**.

$$\sum_{i=1}^{7} \text{MaxMarks}_i = 30.0 + 20.0 + 15.0 + 10.0 + 10.0 + 10.0 + 5.0 = 100.0$$

#### Detailed Criteria, Weights, and Anchor Descriptions

1. **`technical_knowledge` (Technical / Job-Role Knowledge) — 30.0 Marks**
   - **Description:** Foundational and role-specific technical mechanisms, concepts, and domain competence.
   - **Anchor 0:** Fundamental misconception or no substantive explanation.
   - **Anchor 1:** Recognizes terms but makes major errors.
   - **Anchor 2:** Partly correct with important gaps.
   - **Anchor 3:** Correct concepts and mechanisms for the selected level.
   - **Anchor 4:** Accurate explanation with relevant distinctions, boundaries or counterexamples.

2. **`problem_solving` (Problem-Solving and Reasoning) — 20.0 Marks**
   - **Description:** Logical approach, structured reasoning, trade-off analysis, and failure mode verification.
   - **Anchor 0:** No workable approach presented.
   - **Anchor 1:** Guesses without logical justification.
   - **Anchor 2:** Plausible approach with significant verification gaps.
   - **Anchor 3:** Coherent steps, justified decisions and verification.
   - **Anchor 4:** Compares alternatives, explains trade-offs and checks relevant failure cases.

3. **`practical_application` (Practical Application and Examples) — 15.0 Marks**
   - **Description:** Implementation experience, coursework/personal projects, or well-reasoned hypothetical exercises.
   - **Anchor 0:** No usable example.
   - **Anchor 1:** Generic claims without concrete actions.
   - **Anchor 2:** Relevant example with unclear implementation or outcome.
   - **Anchor 3:** Concrete actions and a plausible outcome or verification method.
   - **Anchor 4:** Specific decisions, contribution, checks and limitations (accepts coursework or personal projects).

4. **`relevance_completeness` (Relevance and Completeness) — 10.0 Marks**
   - **Description:** Direct responsiveness to interview prompt and thoroughness of coverage.
   - **Anchor 0:** Does not address the question.
   - **Anchor 1:** Addresses peripheral points.
   - **Anchor 2:** Addresses main request but misses important parts.
   - **Anchor 3:** Covers important requested components.
   - **Anchor 4:** Complete, focused and appropriately prioritized.

5. **`communication_clarity` (Communication Clarity) — 10.0 Marks**
   - **Description:** Organization, terminological precision, and coherent articulation.
   - **Anchor 0:** Explanation remains uninterpretable with usable evidence.
   - **Anchor 1:** Disconnected ideas.
   - **Anchor 2:** Understandable main point with organizational gaps.
   - **Anchor 3:** Clear organization and terminology.
   - **Anchor 4:** Precise explanation supported by helpful examples or definitions.

6. **`followup_reflection` (Follow-Up Response and Reflection) — 10.0 Marks**
   - **Description:** Engagement with follow-up probes, clarifying or correcting reasoning under challenge.
   - **Anchor 0:** Does not engage with the probe.
   - **Anchor 1:** Repeats the original answer without new depth.
   - **Anchor 2:** Addresses part of the probe.
   - **Anchor 3:** Addresses it and clarifies or corrects reasoning.
   - **Anchor 4:** Incorporates it coherently and supports revised reasoning with an example or check.

7. **`spoken_delivery` (Spoken Delivery and Intelligibility) — 5.0 Marks**
   - **Description:** Audibility, pacing, and verbal intelligibility from usable audio recordings.
   - **Anchor 0:** Unintelligible despite usable recording.
   - **Anchor 1:** Delivery frequently obscures meaning.
   - **Anchor 2:** Mostly understandable with recurring interference.
   - **Anchor 3:** Understandable pacing and audibility.
   - **Anchor 4:** Consistently easy to follow with useful pauses or emphasis.

### 2.2 Calculation Rules and Partial Evaluation Handling
- **Marks per Criterion:**
  $$\text{EarnedMarks}(c) = \frac{\text{Rating}(c)}{4.0} \times \text{MaxMarks}(c)$$
- **Missing Signals Handling:**
  - If audio is unavailable, `spoken_delivery` rating is `None`.
  - The calculator sets:
    - `assessment_status = "partial"`
    - `assessed_maximum = 95.0`
    - `total_score_100 = None` (**strictly avoiding presenting a 95-mark evaluation as a 100-mark evaluation**)
    - `provisional_normalized_100 = round((assessed_score / 95.0) * 100, 2)`
    - `coverage_percent = 95.0%`
  - If all criteria are missing: `assessment_status = "unassessed"`, `total_score_100 = None`, `coverage_percent = 0.0%`.
- **Human Overrides:** Endpoint `POST /api/rubric/manual-review` updates individual criterion ratings with human reviewer notes and automatically recalculates scores deterministically.

### 2.3 Audit of the 110-Point Anomaly
The research team noted a question regarding:
> *"Check whether Completeness 40 + Technical Depth 35 + Communication Clarity 25 + Relevance 10 totals 110. Explain any actual normalization or cap from the code; do not silently correct it."*

**Code Finding:**
This 110-point scheme originates from the **legacy heuristic scoring function** located in [`backend/app/services/llm_engine.py`](file:///d:/nishanth_work/final_project/backend/app/services/llm_engine.py#L450-L482):
```python
# Lines 450-482 of backend/app/services/llm_engine.py:
# Completeness (0-40 pts): based on word count bins (0, 10, 20, 30, 40)
# Technical depth (0-35 pts): min(35, tech_hits * 7)
# Communication (0-25 pts): min(25, comm_hits * 6)
# Relevance bonus (0-10 pts): min(10, overlap * 2)

raw = completeness + tech_score_raw + comm_score_raw + relevance_bonus
score = max(10, min(100, raw))
```
- **Sum Verification:**
  $$40 + 35 + 25 + 10 = 110 \text{ maximum raw points}$$
- **Actual Code Normalization / Capping Behavior:**
  - The code does **NOT** normalize by dividing by 110.
  - Instead, line 481 applies a **hard clip/cap**:
    $$\text{score} = \max(10, \min(100, \text{raw}))$$
  - Any raw score between 100 and 110 is truncated to 100. Any score below 10 is floored at 10.
- **Architectural Context:** This legacy function in `llm_engine.py` was superseded by the versioned 100-mark rubric engine `interview_practice_100_v1` in `backend/app/rubric/config.py`, which strictly sums to 100.0 without clipping.

---

## 3. DATASETS AND DATA GOVERNANCE AUDIT

| Dataset Name | Documented Source / URL | License | Total Records | Documented Splits | Data Nature | Overlap / Leakage Safeguards |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **PreMock Multi-Task (`interview_dataset.csv`)** | Local repository: [`backend/data/interview_dataset.csv`](file:///d:/nishanth_work/final_project/backend/data/interview_dataset.csv) | CC0-1.0 (4,915), Apache-2.0 (4,875), CC-BY-4.0 (210) | **10,000** | Train: 8,000 (80%)<br>Val: 1,129 (11.29%)<br>Test: 871 (8.71%) | Synthetic LLM-labeled + scenario templates | Fixed disjoint record indices across tasks: `resume_extract` (4,875), `role_question` (2,565), `followup` (2,560) |
| **FER-2013 Facial Emotions** | Kaggle / ICML 2013 Challenges in Representation Learning | Academic research use | **35,887** | Train: 28,709<br>Val: 5,742 (20% of train)<br>Test: **7,178** | Real human face photographs | Official fixed test set; `train_v2.py:L22` loads `X_test.npy` at the end only |
| **MPIIGaze** | Max Planck Institute for Informatics (MPII) | Non-commercial academic | **213,659** | 15 participant partitions | Real natural webcam gaze | Evaluated cross-participant; right-eye crops aligned with MediaPipe FaceMesh |
| **Common Voice Indian English Accent** | HuggingFace: `ishands/commonvoice-indian_accent` | CC0-1.0 / MPL | **110,088** | Manifest: [`full_speaker_split.json`](file:///d:/nishanth_work/final_project/ml/asr_training/full_speaker_split.json)<br>Train: 2,460 speakers<br>Val / Test: disjoint | Real human speech recordings | Strict speaker grouping by `client_id`; 100% disjoint speaker separation verified in `fix_speaker_split.py` |

---

## 4. TRAINING EVIDENCE AUDIT

### 4.1 Model M1: Facial Emotion Transfer Learning (MobileNetV2)
- **Status:** **Completed Training (Full experimental artifacts verified)**.
- **Source Script:** [`ml/emotion_v2/train_v2.py`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py).
- **Saved Evidence Files:**
  - Evaluation Report: [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json)
  - Training History: [`ml/emotion_v2/outputs/training_history_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/training_history_v2.json)
  - Confusion Matrix Array: [`ml/emotion_v2/outputs/confusion_matrix_v2.npy`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/confusion_matrix_v2.npy)
- **Base Model:** MobileNetV2 pretrained on ImageNet (weights loaded from Keras applications).
- **Preprocessing:** 48x48 grayscale resized and channel-repeated to $96 \times 96 \times 3$ RGB; scaled via MobileNet preprocessing (`[-1, 1]`).
- **Data Augmentation:** Train split only; random horizontal flip, rotation ($\pm 15^\circ$), zoom ($\pm 10\%$), translation ($\pm 10\%$), brightness ($\pm 20\%$), contrast ($\pm 15\%$).
- **Imbalance Handling:** Random oversampling on minority classes (threshold $2.5 \times$) plus `compute_class_weight('balanced')`.
- **Training Protocol:**
  - Phase 1 (Warm-up): 8 epochs, backbone frozen, Adam ($\text{lr} = 1\times 10^{-3}$), label smoothing = 0.1.
  - Phase 2 (Fine-tuning): 60 epochs max with Early Stopping ($\text{patience} = 12$, restore best weights), unfreezing from layer 100, Adam ($\text{lr} = 2\times 10^{-4}$), label smoothing = 0.05.
- **Hardware & Runtime:** Total training time: **8,241.6 seconds (~2.29 hours)**.
- **Checkpoint Identity:** `emotion_model_v2.keras` (Size: 27.26 MB; saved best val accuracy: 64.47%).

### 4.2 Model M2: Gaze & Eye-Contact Regressor (Custom CNN)
- **Status:** **Calibration Complete; Training Executed Externally**.
- **Source Script:** [`ml/eye_contact/train.py`](file:///d:/nishanth_work/final_project/ml/eye_contact/train.py), [`calibrate_eye_contact.py`](file:///d:/nishanth_work/final_project/ml/eye_contact/calibrate_eye_contact.py).
- **Base Architecture:** Custom 3-block CNN (`Conv2D` 32 $\rightarrow$ 64 $\rightarrow$ 128 with `BatchNorm` and `MaxPool2D`) + `Dense(256)` + `Dense(128)` + `Dense(2, linear)` (Pitch, Yaw).
- **Hyperparameters:** Adam optimizer, MSE loss, MAE metric, epochs = 20, batch size = 128.
- **Artifact Present:** Calibrated thresholds file [`ml/eye_contact/eye_contact_thresholds.json`](file:///d:/nishanth_work/final_project/ml/eye_contact/eye_contact_thresholds.json).
- **Artifact Missing Locally:** `backend/ml_models/gaze_model.keras` and `gaze_training_history.json` were not checked into this Git repository.

### 4.3 Model M3: Whisper ASR Fine-Tuning (LoRA on Common Voice)
- **Status:** **Scripts and Splits Complete; Training Executed Externally**.
- **Source Scripts:** [`ml/asr_training/train_full.py`](file:///d:/nishanth_work/final_project/ml/asr_training/train_full.py), [`train_20k.py`](file:///d:/nishanth_work/final_project/ml/asr_training/train_20k.py), [`retrain_pilot_speaker_safe.py`](file:///d:/nishanth_work/final_project/ml/asr_training/retrain_pilot_speaker_safe.py).
- **Base Model:** `openai/whisper-base.en`.
- **Quantization:** 8-bit quantized backbone via `BitsAndBytesConfig(load_in_8bit=True)`.
- **LoRA Configuration:**
  - Rank: $r = 8$
  - Alpha: $\alpha = 16$
  - Dropout: $0.05$
  - Target Modules: `["q_proj", "v_proj"]`
  - Trainable Bias: `none`
- **Training Parameters:** Learning rate: $1\times 10^{-4}$, effective batch size = 8 ($2 \times 4$ gradient accumulation), FP16 mixed precision.
- **Artifact Missing Locally:** Weights directory `ml/asr_model/whisper_indian_accent_lora_20k` is not committed locally.

---

## 5. ASR RESULTS AUDIT (WER & LATENCY CLAIMS)

### 5.1 Audit of the "17.33% Normalized WER" Claim
- **Search Result:** A comprehensive search across all files, Git commit history, and logs for `"17.33"` yielded **ZERO occurrences** in any project script or log.
- **Code Capability vs. Saved Results:**
  - The script [`ml/asr_training/evaluate_20k_vs_baseline.py`](file:///d:/nishanth_work/final_project/ml/asr_training/evaluate_20k_vs_baseline.py) was written to evaluate the 20k LoRA model against baseline on 500 held-out samples.
  - However, no execution log or output file (`eval_results.json`) was generated or saved to this workspace.
- **Actual Saved ASR Result in Workspace:**
  - In [`ml/asr_training/inspect_training_loss.py`](file:///d:/nishanth_work/final_project/ml/asr_training/inspect_training_loss.py#L95-L101), the pilot model (50 steps on 100 samples) logged:
    - Final Training Loss: **15.70**
    - Evaluation Loss: **3.48**
- **Assessment of 17.33% WER Claim:** **Not available in this workspace**. (Likely generated in Colab/cloud during a run whose logs were not committed).

### 5.2 Audit of the "823.89 ms Latency" Claim
- **Search Result:** A workspace-wide search for `"823.89"` yielded **ZERO occurrences**.
- **Timing Evidence Present:**
  - [`ml/asr_training/timing_benchmark.py`](file:///d:/nishanth_work/final_project/ml/asr_training/timing_benchmark.py) defines a 10-step benchmark script to compute training and evaluation speed per sample.
  - No saved benchmark log containing 823.89 ms exists in the workspace.
- **Assessment of 823.89 ms Latency Claim:** **Not available in this workspace**.

---

## 6. FACIAL EMOTION RESULTS AUDIT (63.96% ACCURACY, 63.89% F1)

### 6.1 Verification of Reported Metrics
- **Assessment:** **Supported by saved results**.
- **Evidence File:** [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json).

```json
{
  "model": "emotion_model_v2.keras",
  "backbone": "MobileNetV2 (ImageNet pretrained)",
  "input_shape": [96, 96, 3],
  "test_accuracy": 0.6395932014488716,
  "macro_f1": 0.6248157700944451,
  "weighted_f1": 0.6389076196598744,
  "macro_precision": 0.6254446559203596,
  "macro_recall": 0.6277607763227131,
  "val_accuracy_best": 0.644723117351532,
  "baseline_accuracy": 0.6172,
  "improvement_pp": 2.24
}
```

### 6.2 Per-Class Breakdown (Held-Out Test Set, $N = 7,178$)

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **Angry** | 56.03% | 53.34% | 54.65% | 958 |
| **Disgust** | 62.28% | 63.96% | 63.11% | 111 |
| **Fear** | 54.98% | 43.16% | 48.36% | 1,024 |
| **Happy** | 85.89% | 82.02% | 83.91% | 1,774 |
| **Neutral** | 55.80% | 60.83% | 58.21% | 1,233 |
| **Sad** | 49.61% | 55.49% | 52.38% | 1,247 |
| **Surprise** | 73.22% | 80.63% | 76.75% | 831 |
| **Macro Average** | **62.54%** | **62.78%** | **62.48%** | 7,178 |
| **Weighted Average** | **64.19%** | **63.96%** | **63.89%** | 7,178 |

### 6.3 Confusion Matrix ($7 \times 7$)
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

### 6.4 Origin of the 7,178 Images and Data Leakage Audit
- **Origin:** In the standard Kaggle / ICML FER-2013 distribution processed by [`ml/emotion/preprocess.py`](file:///d:/nishanth_work/final_project/ml/emotion/preprocess.py), the `test/` directory contains exactly 7,178 images (PublicTest 3,589 + PrivateTest 3,589).
- **Validation vs. Test Separation:**
  - They were **NOT** combined.
  - In [`ml/emotion_v2/train_v2.py:L217-L219`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py#L217-L219), a 20% stratified split was taken from `X_train.npy` (28,709 images) to form `X_val` (5,742 images).
  - All early stopping and model checkpointing monitored `val_accuracy` on this 20% training split.
  - `X_test.npy` (7,178 images) was loaded strictly at line 333 for the final one-shot evaluation.
  - **Verdict:** Zero test images influenced training, tuning, or checkpoint selection.
- **v1 Baseline Performance:** Documented as **61.72%**; v2 demonstrates a verified **+2.24 percentage point improvement**.

---

## 7. GAZE RESULT AUDIT (0.100 RADIANS MAE CLAIM)

### 7.1 Audit of the "0.100 Radians Validation MAE" Claim
- **Search Result:** The literal value `"0.100"` does not appear in any evaluation log.
- **Code Origin Discovery:**
  - In [`ml/eye_contact/calibrate_eye_contact.py:L44`](file:///d:/nishanth_work/final_project/ml/eye_contact/calibrate_eye_contact.py#L44):
    ```python
    center_mask = (np.abs(y_val[:, 0]) < 0.1) & (np.abs(y_val[:, 1]) < 0.1)
    ```
  - The string `< 0.1` was a heuristic filtering threshold used to select validation samples where the subject was looking approximately toward the camera ($\pm 0.1\text{ rad} \approx \pm 5.73^\circ$).
  - **Assessment:** **Incorrect / Misinterpreted Claim**. The value 0.1 was a data filtering condition, not a measured validation MAE.

### 7.2 Nature of the Error Metric
- The gaze model targets are 2 independent continuous outputs: Pitch and Yaw.
- In [`calibrate_eye_contact.py:L85-L90`](file:///d:/nishanth_work/final_project/ml/eye_contact/calibrate_eye_contact.py#L85-L90), errors are computed as:
  $$\text{Pitch Error} = |y_{\text{pred, 0}} - y_{\text{val, 0}}|$$
  $$\text{Yaw Error} = |y_{\text{pred, 1}} - y_{\text{val, 1}}|$$
- **Finding:** This measures **target-wise absolute scalar error in radians**, NOT 3D angular vector error ($\arccos$).
- **Calibrated Parameters in Production:**
  - `center_pitch`: -0.15278 rad
  - `center_yaw`: -0.07262 rad
  - `pitch_threshold`: 0.060 rad ($\approx 3.44^\circ$)
  - `yaw_threshold`: 0.075 rad ($\approx 4.30^\circ$)
- **Independent Eye-Contact Validation:** **Not performed**. No separate labeled test set for binary eye-contact classification exists in the workspace.

---

## 8. COMPARISONS AND INTEGRATION AUDIT

| Comparison / Integration Test | Status | Evidence File | Details |
| :--- | :---: | :--- | :--- |
| **Base-Whisper vs. LoRA 20k** | **Not performed** | `ml/asr_training/evaluate_20k_vs_baseline.py` | Script exists, but evaluation output was not saved locally. |
| **Emotion v1 vs. v2** | **Supported by saved results** | `ml/emotion_v2/outputs/eval_report_v2.json` | v1: 61.72% vs v2: 63.96% (+2.24 pp). Evaluated on identical 7,178 test images. |
| **Human-Review Agreement Study** | **Not performed** | `backend/app/routes/rubric.py` | Route `/api/rubric/manual-review` functional; inter-annotator study never performed. |
| **End-to-End Session Execution** | **Supported by saved results** | `backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json` | Complete mock session report saved with verifiable quotes and partial rubric score. |
| **Unit Test Verification** | **Reproduced** | `backend/tests/test_rubric_100.py` | **10/10 tests passing in 0.018s**. Validates invariants, missing signals, and quote checks. |
| **Posture Analysis Module** | **Absent / Placeholder** | `backend/app/rubric/schemas.py` | Explicit placeholder (`posture: null`). No model or landmark pipeline exists. |
| **Voice / Prosody Acoustic Module** | **Absent / Placeholder** | `backend/app/rubric/evaluator.py` | No DSP models (pitch, jitter, shimmer). Lexical filler fallback only. |

---

## 9. CONTRIBUTIONS, REFERENCES, AND CLAIM AUDITING

### 9.1 Implemented Team Contributions
1. **Deterministic 100-Mark Rubric Engine (`interview_practice_100_v1`):** Mathematical calculation with integer anchors (0–4) across 7 criteria, verifiable quote matching, and equal topic group weighting.
2. **Autonomous Multi-Turn Interview State Machine:** Local phased questioning (Intro $\rightarrow$ General $\rightarrow$ Technical $\rightarrow$ Closing), dynamic turn policies, and private `expected_points` suppression.
3. **Multimodal Bias Isolation Boundary:** Formal separation of vision metrics (emotion, gaze) into non-scoring coaching observations.
4. **Disjoint Speaker-Partitioning Scheme:** Creation of `full_speaker_split.json` across 110,088 recordings to prevent speaker identity leakage.
5. **MobileNetV2 Transfer Learning Pipeline:** Fine-tuned on FER-2013 achieving 63.96% test accuracy on 7,178 images.

### 9.2 Documented References
- **Whisper:** Radford et al., *Robust Speech Recognition via Large-Scale Weak Supervision*, 2022.
- **LoRA:** Hu et al., *LoRA: Low-Rank Adaptation of Large Language Models*, 2021.
- **MobileNetV2:** Sandler et al., *MobileNetV2: Inverted Residuals and Linear Bottlenecks*, CVPR 2018.
- **FER-2013:** Goodfellow et al., *Challenges in Representation Learning: A report on three machine learning contests*, ICML 2013.
- **MPIIGaze:** Zhang et al., *MPIIGaze: Real-World Dataset and Deep Appearance-Based Gaze Estimation for Freely Moving Users*, IEEE TPAMI 2017.
- **MediaPipe:** Lugaresi et al., *MediaPipe: A Framework for Building Perception Pipelines*, 2019.

---

## 10. COMPREHENSIVE CLAIM ASSESSMENT TABLE

| Claim | Evidence | Assessment | Missing information |
| :--- | :--- | :---: | :--- |
| **1. 100-mark rubric is deterministic and weights sum to 100** | [`backend/app/rubric/config.py:L104`](file:///d:/nishanth_work/final_project/backend/app/rubric/config.py#L104), [`tests/test_rubric_100.py`](file:///d:/nishanth_work/final_project/backend/tests/test_rubric_100.py) | **Reproduced** | None. Fully verified by 10/10 passing unit tests. |
| **2. Question engine runs locally without paid cloud APIs** | [`backend/app/services/local_interview_model.py`](file:///d:/nishanth_work/final_project/backend/app/services/local_interview_model.py), [`backend/app/routes/interview.py`](file:///d:/nishanth_work/final_project/backend/app/routes/interview.py) | **Supported by code** | None. OpenRouter is completely unreferenced in active routes. |
| **3. Legacy scoring sum totals 110 points** | [`backend/app/services/llm_engine.py:L450-L482`](file:///d:/nishanth_work/final_project/backend/app/services/llm_engine.py#L450-L482) | **Supported by code** | Sums to 110 ($40+35+25+10$), but code applies `min(100, raw)` cap, not normalization. |
| **4. FER-2013 Emotion accuracy is 63.96% with 63.89% weighted F1** | [`ml/emotion_v2/outputs/eval_report_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/eval_report_v2.json), [`training_history_v2.json`](file:///d:/nishanth_work/final_project/ml/emotion_v2/outputs/training_history_v2.json) | **Supported by saved results** | Checkpoint binary `emotion_model_v2.keras` external to Git repo. |
| **5. 7,178 emotion images were not leaked into training** | [`ml/emotion_v2/train_v2.py:L217, L333`](file:///d:/nishanth_work/final_project/ml/emotion_v2/train_v2.py#L217) | **Supported by saved results** | None. Verified: 20% val split taken from train set; test set kept held-out. |
| **6. Gaze model achieved 0.100 radians validation MAE** | [`ml/eye_contact/calibrate_eye_contact.py:L44`](file:///d:/nishanth_work/final_project/ml/eye_contact/calibrate_eye_contact.py#L44) | **Incorrect** | 0.1 was a heuristic center-filtering condition (`abs < 0.1`), not an empirical MAE. |
| **7. Whisper fine-tuning achieved 17.33% normalized WER** | Whole repository search | **Not available** | Zero occurrences in codebase or logs. No test evaluation log exists locally. |
| **8. ASR latency is 823.89 ms** | Whole repository search | **Not available** | Zero occurrences in codebase or logs. Benchmark script exists but no output. |
| **9. Posture analysis is implemented and functional** | [`backend/app/rubric/schemas.py`](file:///d:/nishanth_work/final_project/backend/app/rubric/schemas.py), [`frontend/.../page.tsx:L743`](file:///d:/nishanth_work/final_project/frontend/src/app/interview/%5Bid%5D/page.tsx#L743) | **Incorrect** | Explicit placeholder (`posture: null`). No model or vision pipeline exists. |
| **10. Acoustic voice/prosody model is functional** | [`backend/app/rubric/evaluator.py:L449`](file:///d:/nishanth_work/final_project/backend/app/rubric/evaluator.py#L449) | **Incorrect** | No DSP feature models (pitch/jitter/shimmer). Rule-based filler counter only. |
| **11. System includes "Eight Custom-Trained Models"** | Workspace inspection | **Incorrect** | Only 3 training pipelines exist (1 with saved results). Rest are rule-based/placeholders. |
| **12. Multi-task dataset contains 10,000 structured samples** | [`backend/data/interview_dataset.csv`](file:///d:/nishanth_work/final_project/backend/data/interview_dataset.csv) | **Supported by saved results** | None. Exactly 10,000 rows across 3 tasks and 17 columns verified. |
| **13. Speaker-disjoint ASR split prevents identity leakage** | [`ml/asr_training/full_speaker_split.json`](file:///d:/nishanth_work/final_project/ml/asr_training/full_speaker_split.json), [`fix_speaker_split.py`](file:///d:/nishanth_work/final_project/ml/asr_training/fix_speaker_split.py) | **Supported by saved results** | Disjoint speaker IDs verified across all 110,088 recordings. |
| **14. End-to-end interview session successfully completes** | [`backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json`](file:///d:/nishanth_work/final_project/backend/data/reports/7dcbdb75-fa24-4bfc-936f-b4359c098573.json) | **Supported by saved results** | None. Full JSON session report preserved on disk. |
