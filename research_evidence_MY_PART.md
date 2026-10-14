# Empirical Research Evidence Audit: PreMock AI (Workspace: MY_PART)

**Project Title:** AI-Powered Video Interview Practice Platform with Automated Performance Evaluation and Personalized Feedback Reports  
**Repository Path:** `D:\project phase 2\final_project-1`  
**Workspace Identifier:** `MY_PART`  
**Git Commit Hash:** `7d5696f206d09b65b8038e4683fee952d22454ad`  
**Git Branch:** `main`  
**Date of Audit:** October 13, 2026  
**Auditor:** DeepMind Antigravity Pair Programmer  

---

## 1. FINAL IMPLEMENTATION AUDIT

### 1.1 Question Engine & Dual-Path Architecture
The repository implements a **dual-path question and evaluation architecture**:

1. **Active Primary Path (Live Frontend):**
   - **Endpoint Invocation:** [frontend/src/app/interview/[id]/page.tsx:L573-L580](file:///d:/project%20phase%202/final_project-1/frontend/src/app/interview/%5Bid%5D/page.tsx#L573-L580) queries `POST /api/interview/generate-question` and `POST /api/interview/evaluate-answer`.
   - **Backend Implementation:** [backend/app/services/interview_llm_service.py](file:///d:/project%20phase%202/final_project-1/backend/app/services/interview_llm_service.py) routes calls through **OpenRouter API** (`https://openrouter.ai/api/v1`).
   - **Active Models:** Model failover cascade: `meta-llama/llama-3.1-8b-instruct:free` $\rightarrow$ `mistralai/mistral-7b-instruct:free` $\rightarrow$ `qwen/qwen-2-7b-instruct:free`.
   - **Static Fallback:** If all external API calls fail or timeout (30.0s), `interview_llm_service.py:L101-L108` and `L194-L207` return static fallback objects:
     - Fallback Question: `"Could you elaborate on your experience as a {job_role}, specifically focusing on the skills mentioned in your resume?"`
     - Fallback Score: Fixed score of 75 (Relevance 80, Tech Depth 70, Clarity 75, Completeness 75).

2. **In-Memory Session Engine (Secondary / Alternative Path):**
   - **Endpoint Invocation:** `POST /api/setup`, `POST /api/answer`, `POST /api/evaluate` in [backend/app/routes/interview.py:L16-L50](file:///d:/project%20phase%202/final_project-1/backend/app/routes/interview.py#L16-L50).
   - **Backend Implementation:** [backend/app/services/llm_engine.py](file:///d:/project%20phase%202/final_project-1/backend/app/services/llm_engine.py) provides a stateful `LLMEngine` class.
   - **Model Options:** Uses `llama-3.1-70b-versatile` (if `GROQ_API_KEY` configured), `gpt-4o` (if `OPENAI_API_KEY` configured), or falls back to a **fully offline, deterministic 100-mark heuristic evaluator** with 60 curated static questions (15 per role across Full Stack, Frontend, Backend, DevOps).

### 1.2 Microservice Topology & Port Allocations
Framework conflicts between TensorFlow 2.15/Keras and PyTorch 2.5/CUDA are resolved through isolated virtual environments:

| Port | Service Name | Executable Environment | Script / App | Functioning State & Checkpoint |
| :---: | :--- | :--- | :--- | :--- |
| **8000** | Main API Gateway | `backend/venv/Scripts/python.exe` | `uvicorn app.main:app` | **Functioning.** Coordinates routes, MediaPipe FaceMesh, and proxies. |
| **8001** | Gaze Inference | `backend/gaze_venv/Scripts/python.exe` | `gaze_service_server.py` | **Functioning.** Loads `backend/ml_models/gaze_model.keras` (4.7 MB). |
| **8002** | Emotion Inference | `backend/emotion_venv/Scripts/python.exe` | `emotion_service_server.py` | **Functioning.** Loads `backend/ml_models/emotion_model.keras` (70.6 MB, v1 CNN). |
| **8003** | Local Whisper ASR | `ml/asr_venv/Scripts/python.exe` | `asr_server.py` | **Functioning.** Loads `openai/whisper-base.en` + LoRA `checkpoint-1200` (1.18 MB). |
| **3000** | Next.js Frontend | Node.js 18+ runtime | `npm run dev` | **Functioning.** Next.js 16 App Router UI. |

---

## 2. COMPLETE RUBRIC & MATHEMATICAL VERIFICATION

### 2.1 Mathematical Discrepancy: The 110-Point Sum
In [backend/app/services/llm_engine.py:L450-L482](file:///d:/project%20phase%202/final_project-1/backend/app/services/llm_engine.py#L450-L482), the deterministic scoring rubric defines four component scores:

1. **Completeness (0 to 40 points):**
   - 0 words: 0 pts
   - $1 \le \text{word\_count} < 20$: 10 pts
   - $20 \le \text{word\_count} < 50$: 20 pts
   - $50 \le \text{word\_count} < 100$: 30 pts
   - $\ge 100$ words: 40 pts
2. **Technical Depth (0 to 35 points):**
   - Matches against `TECH_TERMS` (68 keywords).
   - $\text{tech\_score\_raw} = \min(35, \text{tech\_hits} \times 7)$
3. **Communication Clarity (0 to 25 points):**
   - Matches against `COMM_MARKERS` (22 discourse markers).
   - $\text{comm\_score\_raw} = \min(25, \text{comm\_hits} \times 6)$
4. **Relevance Bonus (0 to 10 points):**
   - Non-stopword token intersection with question.
   - $\text{relevance\_bonus} = \min(10, \text{overlap} \times 2)$

$$\text{Sum of Maximum Points} = 40 + 35 + 25 + 10 = \mathbf{110\text{ points}}$$

#### Code Cap & Normalization Mechanism:
Line 481 of `llm_engine.py` handles the surplus through clamping:
```python
raw = completeness + tech_score_raw + comm_score_raw + relevance_bonus
score = max(10, min(100, raw))
```
- **Finding:** The rubric is an **augmented 110-point system capped at 100**. A candidate can attain a perfect score of 100 without achieving full marks in all four criteria (e.g., scoring $40 + 35 + 25 + 0 = 100$ without any relevance bonus).
- **Floor:** The minimum score for any attempted answer with at least 1 word is floored at **10 points** via `max(10, ...)`.

### 2.2 Sub-Score Scaling
Sub-scores are independently normalized to 0–100 in lines 532–534:
- $\text{Technical Score} = \min(100, \lfloor \text{Mean}(\text{tech\_vals}) \times \frac{100}{35} \rfloor)$
- $\text{Communication Score} = \min(100, \lfloor \text{Mean}(\text{comm\_vals}) \times \frac{100}{25} \rfloor)$
- $\text{Answer Relevance} = \min(100, \lfloor \text{Mean}(\text{rel\_vals}) \times \frac{100}{10} \rfloor)$
- $\text{Overall Score} = \text{Mean}(\text{Question Scores})$

### 2.3 Qualitative Anchor Descriptions & Feedback Tiers
Lines 484–503 define verbal feedback bands:
- **$\ge 80$:** *"Strong, detailed answer with good technical depth. You demonstrated clear reasoning and relevant specifics."*
- **$60 \le \text{Score} < 80$:** *"Solid response covering the core points. Adding more concrete examples or trade-off analysis would strengthen it further."*
- **$40 \le \text{Score} < 60$:** *"Partial answer — you touched on the right area but lacked depth. Try to explain the 'why' and include specific technical details."*
- **$< 40$:** *"The answer was too brief or did not address the question directly. Practice structuring responses: state your approach, give an example, explain trade-offs."*

### 2.4 Human Overrides & Missing-Signal Protocol
- **Human Overrides:** **Not implemented.** There are no administrative review endpoints, database override flags, or manual adjustment interfaces in this workspace.
- **Unanswered Questions:** If an interview is terminated with 0 answers, `_minimal_evaluation()` sets all scores to 0.
- **Missing Sensor Signals:**
  - If video frames drop or face detection fails, `eye_contact` and `face_present` record as `null` in PostgreSQL. Content scores are completely isolated and evaluated independently.
  - If STT fails, the user can type or retry without grading penalties.

---

## 3. DATASETS & SPLIT MANIFESTS

### 3.1 Dataset Inventory & Manifest Verification

| Dataset Name | Domain / Origin | Source URL / Manifest | License | Total Records | Split Partition (Train / Val / Test) | Overlap Verification Evidence |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Common Voice Indian Accent** | Real crowdsourced speech | `ishands/commonvoice-indian_accent` (Hugging Face) | CC0 / MPL 2.0 | ~40,000+ | **Train:** 20,000 (Batch 1), 20,000 (Batch 2)<br>**Val:** 200<br>**Test:** 500 (held-out) | Disjoint by `client_id` (1,964 train, 245 val, 245 test) in `full_speaker_split.json`. Assertion in `evaluate_20k_vs_baseline.py:L82-L83`. |
| **MPIIGaze** | Real eye-tracking camera images | Max Planck Institute for Informatics | Scientific Non-Commercial | **107,056** processed crops | **Train:** 103,254 (`p00`–`p10`)<br>**Val:** 2,300 (`p11`–`p12`)<br>**Test:** 1,502 (`p13`–`p14`) | Disjoint participant IDs in `ml/eye_contact/preprocess.py:L14-L16`. |
| **FER-2013** | Real crawled web face images | Kaggle (Challenges in Representation Learning 2013) | Academic / Research | **35,887** | **Train:** 22,967 (80% of 28,709)<br>**Val:** 5,742 (20% of 28,709)<br>**Test:** **7,178** (held-out) | Partitioned via `X_train.npy` and `X_test.npy` in `ml/emotion/dataset/processed/`. |
| **WhissleAI Meta STT** | Real technical interview speech | `WhissleAI/Meta_STT_EN-IN_Tech_Interviews` (Hugging Face) | `whissle-inference-only-1.0` | 59,204 | **Train:** 58,000<br>**Val:** 1,204<br>**Test:** None | **Unused for training in this workspace.** Blocked by 401 Gated Access. |

---

## 4. MODEL TRAINING EVIDENCE & CHECKPOINTS

### 4.1 Summary of Models Trained in This Workspace

```
Models in Workspace:
├── ASR (Speech)
│   ├── whisper_indian_accent_lora_20k/checkpoint-1200  [COMPLETED & DEPLOYED]
│   └── whisper_indian_accent_40k_experiment/checkpoint-500  [COMPLETED EXPERIMENT]
├── Gaze (Eye Contact)
│   └── gaze_model.keras  [COMPLETED & DEPLOYED]
└── Emotion (Facial)
    ├── emotion_model.keras (v1 CNN)  [COMPLETED & DEPLOYED]
    └── emotion_model_v2.keras (v2 MobileNetV2)  [COMPLETED EXPERIMENT]
```

### 4.2 Exact Training Configurations

| Model | Base Architecture | Checkpoint Path | Hyperparameters | Optimizer / Loss | Training Logs Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ASR 20k LoRA** | `openai/whisper-base.en` (39M params) | `ml/asr_model/whisper_indian_accent_lora_20k/checkpoint-1200` | $r=8, \alpha=16$, dropout 0.05, targets: `q_proj, v_proj`, 8-bit QLoRA, batch 2, accum 8, max steps 1,250 | AdamW, lr $1\times 10^{-4}$, fp16 | Checkpoint directory + `training_args.bin` |
| **ASR 40k LoRA** | `checkpoint-1200` continuation | `ml/asr_model/whisper_indian_accent_40k_experiment/checkpoint-500` | Same LoRA config, batch 2, accum 8, max steps 1,250 | AdamW, lr $3\times 10^{-5}$, fp16 | Checkpoint directory + `experiment_summary.json` |
| **Gaze CNN** | 3-layer custom CNN + BatchNorm + Dense(256, 128, 2) | `backend/ml_models/gaze_model.keras` | Input: 48×36×1, batch 128, 13 epochs (early stopping patience 5) | Adam, MSE loss, MAE metric | `backend/ml_models/gaze_training_history.json` |
| **Emotion v1** | 6-layer custom CNN + BatchNorm + Dense(512, 7) | `backend/ml_models/emotion_model.keras` | Input: 48×48×1, batch 64, data augmentation (flip, rotate) | Adam, lr 0.001, Categorical Crossentropy | Model file (70.6 MB); training script `ml/emotion/train.py` |
| **Emotion v2** | MobileNetV2 (ImageNet pretrained backbone) | `backend/ml_models/emotion_model_v2.keras` | Input: 96×96×3, batch 32, Phase 1 (8 ep, frozen), Phase 2 (60 ep, unfreeze top-100) | Adam, Phase 1 lr 0.001, Phase 2 lr $1\times 10^{-4}$ | `ml/emotion_v2/outputs/eval_report_v2.json` + `training_history_v2.json` |

---

## 5. ASR RESULT VERIFICATION (17.33% WER & 823.89 ms LATENCY)

### 5.1 Evidence for 17.33% Normalized WER
- **Log Reference:** [ml/asr_model/whisper_indian_accent_40k_experiment/evaluation_20k_vs_40k_report.json](file:///d:/project%20phase%202/final_project-1/ml/asr_model/whisper_indian_accent_40k_experiment/evaluation_20k_vs_40k_report.json)
- **Evaluation Partition:** 500 audio samples selected via `seed=42` from the disjoint `test` partition of `full_speaker_split.json`.
- **Speaker Count:** Drawn from 245 disjoint test speakers (zero overlap with the 1,964 training speakers).
- **Checkpoint Used:** `ml/asr_model/whisper_indian_accent_lora_20k/checkpoint-1200`.
- **Text Normalization Rules:** Standard `BasicTextNormalizer()` from `transformers.models.whisper.english_normalizer`.
- **Reported Error Metrics:**
  - **Normalized WER:** **17.33%**
  - **Raw WER:** 22.80%
  - **Normalized CER:** 7.93%
  - **Raw CER:** 9.42%
- **Missing Information:** The evaluation script used Hugging Face `evaluate.load("wer")` and did not log individual counts for substitutions ($S$), deletions ($D$), insertions ($I$), or total reference words ($N$).

### 5.2 Evidence for 823.89 ms Latency
- **Timing Boundary:** Measured in [ml/asr_training/evaluate_20k_vs_baseline.py:L109-L127](file:///d:/project%20phase%202/final_project-1/ml/asr_training/evaluate_20k_vs_baseline.py#L109-L127) using `time.time()`:
  - Encompasses `processor.feature_extractor()` + GPU `model.generate(max_new_tokens=225)` + `processor.batch_decode()`.
- **Recorded Values:**
  - Total elapsed time across 500 samples: **411.95 seconds**.
  - Mean latency per sample: $\frac{411.95\text{ s}}{500} = \mathbf{823.89\text{ ms}}$.
- **Hardware:** NVIDIA GeForce RTX 3050 Laptop GPU (4.0 GB VRAM), CUDA 12.1.
- **Batch Size:** 1 (sequential sample-by-sample loop).
- **Warm-Up:** No dedicated pre-warmup pass before the 500-sample benchmark.

---

## 6. EMOTION RESULT VERIFICATION (63.96% ACCURACY & 63.89% F1)

### 6.1 Evaluation Log Export (Emotion v2)
- **Log Reference:** [ml/emotion_v2/outputs/eval_report_v2.json](file:///d:/project%20phase%202/final_project-1/ml/emotion_v2/outputs/eval_report_v2.json)
- **Model Checkpoint:** `emotion_model_v2.keras` (MobileNetV2 transfer learning).
- **Test Sample Size:** **7,178 images** (from `ml/emotion/dataset/processed/X_test.npy`).
- **Summary Metrics:**
  - **Overall Test Accuracy:** **63.96%** (`0.639593`)
  - **Weighted Average F1-Score:** **63.89%** (`0.638908`)
  - **Macro Average F1-Score:** **62.48%** (`0.624816`)
  - **Macro Precision:** 62.54%
  - **Macro Recall:** 62.78%

### 6.2 Per-Class Breakdown & Confusion Matrix
From `eval_report_v2.json` and `confusion_matrix_v2.npy`:

| Class | Precision | Recall | F1-Score | Support ($N$) |
| :--- | :---: | :---: | :---: | :---: |
| **Happy** | 85.89% | 82.02% | **83.91%** | 1,774 |
| **Surprise** | 73.22% | 80.63% | **76.75%** | 831 |
| **Disgust** | 62.28% | 63.96% | **63.11%** | 111 |
| **Neutral** | 55.80% | 60.83% | **58.21%** | 1,233 |
| **Angry** | 56.03% | 53.34% | **54.65%** | 958 |
| **Sad** | 49.61% | 55.49% | **52.38%** | 1,247 |
| **Fear** | 54.98% | 43.16% | **48.36%** | 1,024 |

#### Confusion Matrix:
$$\begin{pmatrix}
511 & 20 & 79 & 38 & 107 & 161 & 42 \\
18 & 71 & 3 & 4 & 3 & 11 & 1 \\
123 & 7 & 442 & 27 & 113 & 209 & 103 \\
65 & 4 & 41 & 1455 & 88 & 76 & 45 \\
106 & 3 & 60 & 58 & 750 & 168 & 88 \\
128 & 8 & 104 & 49 & 186 & 692 & 80 \\
23 & 1 & 75 & 63 & 97 & 2 & 670
\end{pmatrix}$$

### 6.3 Origin of the 7,178 Test Images & Leakage Audit
- **Origin:** Standard FER-2013 has 28,709 training samples and two 3,589-sample test splits (PublicTest + PrivateTest). $3,589 + 3,589 = \mathbf{7,178\text{ images}}$.
- **Leakage Check:** In `ml/emotion_v2/train_v2.py:L22-L25`, `X_test.npy` is loaded **only at final evaluation time**. Training and model selection utilized an 80/20 train/validation split drawn strictly from `X_train.npy` ($28,709 \rightarrow 22,967$ train, $5,742$ validation). Zero test images influenced checkpoint selection.
- **Emotion v1 Results:** `emotion_model.keras` does not have a saved JSON evaluation file in the repository.

---

## 7. GAZE RESULT VERIFICATION (0.100 rad MAE & INDEPENDENT TEST)

### 7.1 Nature of the 0.100 rad Metric
- **Log Reference:** [backend/ml_models/gaze_training_history.json:L40,L55](file:///d:/project%20phase%202/final_project-1/backend/ml_models/gaze_training_history.json#L40)
- **Exact Metric:** **Validation MAE = 0.10036 radians ($\approx 5.75^\circ$)** at Epoch 8.
- **Metric Definition:** In Keras multi-output regression, MAE measures the **mean absolute deviation of pitch and yaw independently**:
  $$\text{MAE} = \frac{1}{2} (|\text{pitch}_{\text{pred}} - \text{pitch}_{\text{true}}| + |\text{yaw}_{\text{pred}} - \text{yaw}_{\text{true}}|)$$
  *It is NOT the 3D angular gaze error $\arccos(\mathbf{g}_1 \cdot \mathbf{g}_2)$.*

### 7.2 Independent Test Evaluation (Executed & Verified)
Evaluated on the held-out test split (`X_test.npy`, $N = 1,502$ samples from participants `p13`, `p14`):
- **Test Loss (MSE):** `0.0229`
- **Overall Test MAE:** **0.1212 radians ($\approx 6.95^\circ$)**
  - **Pitch MAE:** 0.1290 radians ($\approx 7.39^\circ$)
  - **Yaw MAE:** 0.1135 radians ($\approx 6.51^\circ$)

### 7.3 Eye-Contact Classification Calibration
From [ml/eye_contact/eye_contact_thresholds.json](file:///d:/project%20phase%202/final_project-1/ml/eye_contact/eye_contact_thresholds.json):
- `center_pitch`: $-0.15278\text{ rad}$
- `center_yaw`: $-0.07262\text{ rad}$
- `pitch_threshold`: $0.06000\text{ rad}$ ($\approx 3.44^\circ$)
- `yaw_threshold`: $0.07500\text{ rad}$ ($\approx 4.30^\circ$)
- **Validation of Eye Contact:** Eye contact is determined strictly via **geometric thresholding** on predicted angles. There is **no separate ground-truth binary eye-contact classification dataset** or separate F1-score evaluation.

---

## 8. COMPARISONS AND INTEGRATION AUDIT

| Comparison / Integration Item | Status | Verified Finding |
| :--- | :---: | :--- |
| **Whisper 20k LoRA vs. 40k LoRA** | **Completed** | Evaluated on identical 500 Common Voice test samples. 20k: 17.33% WER vs. 40k: 17.04% WER ($\Delta = -0.29\%$). |
| **Base Whisper vs. 20k LoRA** | **Not performed on test set** | Evaluated on 20 pilot samples; zero-shot base Whisper on the 500 test set was not logged in `evaluation_20k_vs_40k_report.json`. |
| **Emotion v1 vs. Emotion v2** | **Not performed side-by-side** | Only v2 metrics are saved in `eval_report_v2.json`. v1 test scores were not preserved. |
| **Human-Review Agreement Study** | **Not performed** | Zero human correlation, inter-rater reliability, or Cohen's $\kappa$ studies exist in the repository. |
| **End-to-End Session Integration** | **Completed** | Validated via `scratch/comprehensive_test.py` across ports 8000, 8001, 8002, 8003. |
| **Posture Analysis Module** | **Absent** | Not implemented in this workspace. Zero code, models, or DB fields. |
| **Voice / Prosody Analysis Module** | **Absent** | Not implemented in this workspace. Zero acoustic pitch, jitter, or energy extractors. |
| **Report Confidence/Stress Timeline** | **Mocked** | Hardcoded static points in `report/[id]/page.tsx:L64-L72`. |

---

## 9. CONTRIBUTIONS & CLAIMS AUDIT

### 9.1 Verified Technical Contributions
1. **Isolated Multi-Framework Microservices Architecture:** Resolved incompatible C++ runtime, TensorFlow, and PyTorch CUDA symbol conflicts by hosting Gaze (Port 8001), Emotion (Port 8002), and Whisper (Port 8003) in decoupled virtual environments behind a FastAPI gateway.
2. **Parameter-Efficient LoRA for Indian English Accents:** Fine-tuned `whisper-base.en` with 8-bit QLoRA on 20,000 speaker-disjoint recordings, achieving 17.33% normalized WER and 823 ms inference on consumer laptop hardware (RTX 3050 4GB).
3. **Person-Independent Gaze Verification:** Implemented subject-disjoint partitioning on MPIIGaze, achieving a test MAE of 0.121 radians ($\approx 6.95^\circ$) with MediaPipe landmark eye alignment.
4. **Deterministic Heuristic Rubric Engine:** Implemented a robust 4-criteria heuristic scoring engine capable of autonomous operation during network dropouts.

### 9.2 Reality Checks on Paper Claims
- **"Eight Independently Trained Models":** **Incorrect / Unsupported.** The workspace contains 3 core ML tasks across 5 checkpoints: 2 ASR adapters (20k, 40k), 1 gaze model, and 2 emotion models (v1, v2). Claiming eight models counts pilot iterations.
- **"Entirely API-Free Local Architecture":** **Incorrect.** Question generation and answer grading default to cloud LLMs (OpenRouter: LLaMA-3.1 / Mistral / Qwen), and authentication uses Supabase cloud. Local inference applies only to vision and ASR.
- **"Fully Integrated Multimodal System":** **Partial.** Posture and vocal prosody modules are completely absent.

---

## 10. COMPACT CLAIMS AND EVIDENCE TABLE

| Claim | Evidence in Codebase / Files | Assessment | Missing Information |
| :--- | :--- | :---: | :--- |
| **Active LLM uses OpenRouter cascade** | [interview_llm_service.py:L23-L29](file:///d:/project%20phase%202/final_project-1/backend/app/services/interview_llm_service.py#L23-L29) | **Supported by code** | None |
| **Rubric uses standard 100-mark additive formula** | [llm_engine.py:L450-L482](file:///d:/project%20phase%202/final_project-1/backend/app/services/llm_engine.py#L450-L482) | **Incorrect** | Maximum scores sum to 110, capped at 100 via `min(100, raw)` |
| **Whisper 20k achieves 17.33% norm WER** | [evaluation_20k_vs_40k_report.json](file:///d:/project%20phase%202/final_project-1/ml/asr_model/whisper_indian_accent_40k_experiment/evaluation_20k_vs_40k_report.json) | **Supported by saved results** | Counts for $S, D, I$, and reference word totals unexported |
| **Whisper latency is 823.89 ms** | [evaluation_20k_vs_40k_report.json](file:///d:/project%20phase%202/final_project-1/ml/asr_model/whisper_indian_accent_40k_experiment/evaluation_20k_vs_40k_report.json) | **Supported by saved results** | Audio clip lengths distribution not broken down per clip |
| **Emotion v2 achieves 63.96% accuracy** | [eval_report_v2.json](file:///d:/project%20phase%202/final_project-1/ml/emotion_v2/outputs/eval_report_v2.json) | **Supported by saved results** | Model is in `ml/emotion_v2`, not active on live Port 8002 |
| **Emotion v1 test results benchmarked** | [backend/ml_models/emotion_model.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/emotion_model.keras) | **Not available** | No saved evaluation metrics file exists for v1 |
| **Gaze achieves 0.100 rad validation MAE** | [gaze_training_history.json](file:///d:/project%20phase%202/final_project-1/backend/ml_models/gaze_training_history.json) | **Supported by saved results** | Measures pitch/yaw absolute error, not 3D vector angular error |
| **Gaze achieves 0.100 rad independent test MAE** | `X_test.npy` evaluation (`test_loss = 0.0229`) | **Incorrect** | Independent test MAE is **0.1212 rad** ($\approx 6.95^\circ$) |
| **Eye-contact binary classification evaluated** | [calibrate_eye_contact.py](file:///d:/project%20phase%202/final_project-1/ml/eye_contact/calibrate_eye_contact.py) | **Not available** | Heuristic angular thresholding only; no labeled test set |
| **WhissleAI dataset used for ASR training** | Inspection task log | **Not available** | Blocked by 401 Gated Access; 0 training runs initiated |
| **Base-Whisper zero-shot evaluated on 500 test set** | `evaluation_20k_vs_40k_report.json` | **Not available** | Script evaluated only 20k vs 40k LoRA checkpoints |
| **Human-evaluator agreement study conducted** | Workspace search | **Not available** | Zero human correlation or inter-rater studies exist |
| **Posture and Prosody modules implemented** | Workspace search | **Not available** | Completely absent in this workspace (`MY_PART`) |
| **Report timeline graph dynamic** | [report/[id]/page.tsx:L64-L72](file:///d:/project%20phase%202/final_project-1/frontend/src/app/report/%5Bid%5D/page.tsx#L64-L72) | **Incorrect** | Hardcoded static points `[{ time: "0:00", confidence: 60 }, ...]` |
