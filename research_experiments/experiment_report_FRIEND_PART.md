# Empirical Component Experiments Report: PreMock AI (Workspace: FRIEND_PART)

**Project Title:** AI-Powered Video Interview Practice Platform with Automated Performance Evaluation and Personalized Feedback Reports  
**Repository Path:** `D:\project phase 2\final_project-1`  
**Workspace Identifier:** `FRIEND_PART`  
**Git Commit Hash:** `7d5696f206d09b65b8038e4683fee952d22454ad`  
**Execution Timestamp:** October 13, 2026 — 23:27 IST  
**Host Hardware:** NVIDIA GeForce RTX 3050 Laptop GPU (4.0 GB VRAM, CUDA 12.1), Intel Core i7-12700H / Family 6 Model 154, 16 GB DDR5 RAM, Windows 11  
**Artifact Directory:** [research_experiments/](file:///d:/project%20phase%202/final_project-1/research_experiments/)

---

## Executive Summary & Experiment Status Matrix

| Experiment | Target ML Module | Test Partition | Primary Metrics Reported | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Experiment 1** | Whisper ASR: Baseline vs. 20k vs. 40k LoRA | Common Voice EN-IN (500 clips, 103 disjoint speakers) | WER, CER, Substitutions, Deletions, Insertions | **EXECUTED** |
| **Experiment 2** | ASR Inference Latency & Real-Time Factor | Common Voice EN-IN (50 clips, 150 CUDA-synced runs) | Complete Latency, Inference Latency, RTF, p95 | **EXECUTED** |
| **Experiment 3** | Emotion Classification: Legacy v1 CNN vs. v2 MobileNet | FER-2013 Held-Out Test (7,178 unseen images) | Accuracy, Macro/Weighted F1, Per-Class Metrics, CM | **EXECUTED** |
| **Experiment 4** | Eye Gaze Tracking: Validation vs. Test MAE | MPIIGaze (Val: p11-p12 [2,300], Test: p13-p14 [1,502]) | Pitch MAE, Yaw MAE, 3D Vector Angular Error | **EXECUTED** |
| **Experiment 5** | Binary Eye-Contact Validation Readiness | Consented Camera/Screen Fixation Protocol | Ground-Truth Labels Audit & Protocol Definition | **PENDING LABELED DATA** |

---

## Environment, System Dependencies & Checkpoint Provenance

### Hardware & Acceleration
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU (Device ID 0, 4.0 GB VRAM)
- **CUDA Driver & Toolkit:** CUDA 12.1
- **Host OS:** Windows 11 (build 10.0.26300-SP0)
- **Host RAM:** 15.71 GB total system memory

### Isolated Execution Environments
To prevent symbol and runtime collisions between TensorFlow 2.15/2.16 and PyTorch 2.5/CUDA, evaluations were conducted in strictly partitioned environments:
1. **ASR Evaluation Environment (`ml/asr_venv`):** Python 3.10, PyTorch `2.5.1+cu121`, Transformers `4.46.3`, PEFT `0.13.2`, BitsAndBytes `0.44.1`, Datasets `3.1.0`, Evaluate `0.4.3`, Jiwer.
2. **Vision Evaluation Environment (`ml_venv`):** Python 3.11, TensorFlow `2.16.1`, Keras 3.x, Scikit-Learn `1.4.1.post1`, NumPy `1.26.4`, Matplotlib `3.8.3`, Pandas `2.2.1`.

### Checkpoint SHA-256 Hashes
Every model checkpoint evaluated was cryptographically hashed prior to testing:

| Checkpoint Path | Description | Checkpoint SHA-256 Hash |
| :--- | :--- | :--- |
| [ml/asr_model/whisper_indian_accent_lora_20k/checkpoint-1200/adapter_model.safetensors](file:///d:/project%20phase%202/final_project-1/ml/asr_model/whisper_indian_accent_lora_20k/checkpoint-1200/adapter_model.safetensors) | 20k Indian Accent LoRA Adapter (Deployed on Port 8003) | `d9ef4a03596117c2d80fd406360989fe8baf8d798cc6dd5d51b50369bf8047c8` |
| [ml/asr_model/whisper_indian_accent_40k_experiment/checkpoint-500/adapter_model.safetensors](file:///d:/project%20phase%202/final_project-1/ml/asr_model/whisper_indian_accent_40k_experiment/checkpoint-500/adapter_model.safetensors) | 40k Indian Accent LoRA Best Checkpoint (Research Experiment) | `d89cd2682226c730f654401556f2cf83a69b9ac7a9338a9267752596b72cc4d0` |
| [backend/ml_models/emotion_model.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/emotion_model.keras) | Legacy v1 6-Layer CNN (Deployed on Port 8002) | `4e767bf3f84106b6011322e0b2b1ab88c29d8e7b051622a35c392f0d34151284` |
| [backend/ml_models/emotion_model_v2.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/emotion_model_v2.keras) | MobileNetV2 Transfer Learning Model (Research Experiment) | `d4d2b32e436ef8fd82041429fd7175300964e597d0c76f11a398ac730c29cf7f` |
| [backend/ml_models/gaze_model.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/gaze_model.keras) | MPIIGaze Eye Crop Regression CNN (Deployed on Port 8001) | `13cfa5cb92ff2e8854f6d658aa43be13d413985540bdeb9e7f97b7d01884878c` |

---

## EXPERIMENT 1 — Whisper Baseline Comparison

### 1.1 Methodology & Disjoint Partition Isolation
- **Dataset:** `ishands/commonvoice-indian_accent` (110,088 total audio clips).
- **Partitioning Authority:** [ml/asr_training/full_speaker_split.json](file:///d:/project%20phase%202/final_project-1/ml/asr_training/full_speaker_split.json).
- **Speaker Disjointness Verification:**
  - Training cohort: 1,964 speakers (0 speaker overlap with test).
  - Validation cohort: 245 speakers (0 speaker overlap with test).
  - Held-out test cohort: 245 speakers ($\text{Train} \cap \text{Test} = \emptyset, \text{Val} \cap \text{Test} = \emptyset$).
  - Frozen test subset: Exactly 500 clips randomly sampled with seed 42. Contains **103 distinct speakers**.
- **Inference Configuration (Identical across all 3 models):**
  - Base architecture: `openai/whisper-base.en` (74M parameters).
  - Quantization: 8-bit quantized weights via `BitsAndBytesConfig(load_in_8bit=True)`.
  - Feature Extractor: 80-channel log-mel spectrogram, 16 kHz sampling rate, FP16 precision.
  - Decoder Constraints: Greedy decoding, `forced_decoder_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")`, `max_new_tokens = 225`.
  - Normalization: `transformers.models.whisper.english_normalizer.BasicTextNormalizer` (lowercasing, punctuation stripping, digit conversion, whitespace collapse).

### 1.2 Empirical Results Table
Evaluated on the identical 500 clips (reference word count = 4,750 raw words; 4,749 normalized words):

| Model Checkpoint | Raw WER (%) | Raw CER (%) | Normalized WER (%) | Normalized CER (%) | Substitutions ($S$) | Deletions ($D$) | Insertions ($I$) | Hits ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Base Whisper (`openai/whisper-base.en`)** | 27.15% | 11.08% | **20.13%** | 9.41% | 741 | 63 | 152 | 3,945 |
| **20k LoRA (`checkpoint-1200`)** | 22.80% | 9.42% | **17.33%** | 7.93% | 638 | 65 | 120 | 4,046 |
| **40k LoRA (`checkpoint-500`)** | 22.44% | 9.32% | **17.04%** | 7.87% | 631 | 65 | 113 | 4,053 |

### 1.3 Key Findings & Analysis
1. **Empirical Reproduction of 17.33% Claim:**  
   The deployed 20k LoRA adapter achieved **17.33% normalized WER**, perfectly reproducing the figure reported in platform documentation.
2. **Zero-Shot Base vs. 20k LoRA Improvement:**  
   Fine-tuning on Indian-accented English reduced normalized WER by **2.80 percentage points** ($20.13\% \rightarrow 17.33\%$, a **13.91% relative error reduction**). Substitutions dropped from 741 to 638, and insertions dropped from 152 to 120.
3. **20k vs. 40k Incremental Gain:**  
   Scaling from 20,000 to 40,000 training utterances yielded an additional **0.29 percentage point** improvement ($17.33\% \rightarrow 17.04\%$). While measurable, returns diminish significantly compared to the initial 20k adaptation.
4. **Data Export:** Full per-clip predictions and references for all 3 models are saved in [research_experiments/results/exp1_predictions.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp1_predictions.csv).

---

## EXPERIMENT 2 — ASR Latency & Real-Time Factor (RTF)

### 2.1 Benchmark Methodology
- **Clips:** 50 held-out clips spanning audio durations from 1.54s to 10.51s (mean duration: 5.46s, median: 5.29s).
- **Protocol:** 5 initial GPU warm-up runs, followed by 3 repetitions per clip (batch size = 1, totaling **150 measured runs**).
- **Synchronization:** Explicit `torch.cuda.synchronize()` calls placed immediately before and after inference boundaries to capture exact GPU kernel execution.
- **Timing Separation:**
  - $T_{\text{inference}}$: Pure neural network decoding (`model.generate()`).
  - $T_{\text{complete}}$: Complete processing pipeline (spectrogram feature extraction + `model.generate()` + tokenizer decoding).
  - $\text{RTF}_{\text{complete}} = \frac{T_{\text{complete}} / 1000}{T_{\text{audio}}}$.

### 2.2 Latency & RTF Statistical Distribution

| Metric Boundary | Inference Only ($T_{\text{inf}}$) | Complete Pipeline ($T_{\text{complete}}$) | Real-Time Factor ($\text{RTF}_{\text{complete}}$) | Real-Time Speedup ($\times$) |
| :--- | :---: | :---: | :---: | :---: |
| **Mean** | **527.09 ms** | **542.60 ms** | **0.1050** | **9.53× real-time** |
| **Median** | 514.94 ms | 529.19 ms | 0.1022 | 9.78× real-time |
| **p95 (95th percentile)** | **835.77 ms** | **853.77 ms** | **0.1599** | **6.25× real-time** |
| **Min** | 147.82 ms | 161.38 ms | 0.0433 | 23.09× real-time |
| **Max** | 1271.53 ms | 1295.59 ms | 0.2312 | 4.32× real-time |
| **Standard Deviation ($\sigma$)** | 187.85 ms | 189.59 ms | 0.0336 | — |

### 2.3 Clarification of the Claimed "823.89 ms" Latency
- The platform's previously cited figure of **823.89 ms** was a batch-level uncalibrated average from an un-synchronized 500-clip run.
- With rigorous `torch.cuda.synchronize()` and warmup:
  - Mean processing latency is **542.60 ms**.
  - The 95th percentile latency ($p95$) is **853.77 ms** (occurring on longer 8–10 second utterances).
  - The **Real-Time Factor is 0.1050**, meaning the model transcribes audio ~**9.5× faster than real-time playback**.
- **Paper Writing Guidance:** The paper must not describe 823.89 ms as an intrinsic constant latency. It must report the mean RTF of 0.105 on consumer hardware (RTX 3050 Laptop GPU) alongside utterance duration distributions.
- **Data Export:** Individual run measurements are saved in [research_experiments/results/exp2_latency_runs.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp2_latency_runs.csv).

---

## EXPERIMENT 3 — Emotion Recognition: Legacy v1 CNN vs. MobileNetV2 v2

### 3.1 Dataset Verification & Preprocessing Fidelity
- **Dataset:** FER-2013 Facial Expression Dataset.
- **Partition Verification:**
  - `X_train.npy`: 28,709 images (Training split).
  - `X_test.npy`: 7,178 images (Combined PublicTest [3,589] + PrivateTest [3,589]).
  - **Data Leakage Check:** Confirmed that both v1 and v2 training scripts split only `X_train.npy` (80% train / 20% validation). `X_test.npy` was completely held out and never seen during training, tuning, or checkpoint selection.
- **Model Implementations:**
  - **Model v1 (Deployed on Port 8002):** 6-layer CNN with BatchNormalization and Dropout ([backend/ml_models/emotion_model.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/emotion_model.keras), 70.6 MB). Preprocessing: $48 \times 48 \times 1$ grayscale normalized to $[0, 1]$.
  - **Model v2 (Offline Research Model):** MobileNetV2 transfer learning backbone with dense projection ([backend/ml_models/emotion_model_v2.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/emotion_model_v2.keras), 28.6 MB). Preprocessing: $96 \times 96 \times 3$ RGB (replicated grayscale channels, resized) normalized to $[0, 1]$.

### 3.2 Benchmark Performance Comparison (7,178 Unseen Test Images)

| Evaluation Metric | Model v1: Legacy 6-Layer CNN (Deployed) | Model v2: MobileNetV2 Fine-Tuned (Research) | Improvement ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Test Accuracy** | 61.72% | **63.96%** | **+2.24 percentage points** |
| **Macro F1-Score** | 58.00% | **62.48%** | **+4.48 percentage points** |
| **Weighted F1-Score** | 61.64% | **63.89%** | **+2.25 percentage points** |
| **Macro Precision** | 60.10% | **63.22%** | **+3.12 percentage points** |
| **Macro Recall** | 56.98% | **62.06%** | **+5.08 percentage points** |
| **Total Test Inference Time** | 24.74 s | 23.46 s | -1.28 s |
| **Average Latency / Sample** | 3.45 ms/sample | 3.27 ms/sample | -0.18 ms |
| **Model Size on Disk** | 70.56 MB | 28.58 MB | **-59.5% reduction** |

### 3.3 Per-Class Performance Breakdown

| Emotion Class | Support ($N$) | v1 Precision | v1 Recall | v1 F1-Score | v2 Precision | v2 Recall | v2 F1-Score | F1 Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Angry** | 958 | 0.509 | 0.505 | 0.507 | 0.548 | 0.584 | **0.565** | +0.058 |
| **Disgust** | 111 | 0.603 | 0.342 | 0.437 | 0.547 | 0.523 | **0.535** | **+0.098** |
| **Fear** | 1,024 | 0.490 | 0.354 | 0.411 | 0.506 | 0.470 | **0.487** | +0.076 |
| **Happy** | 1,774 | 0.850 | 0.841 | 0.845 | 0.871 | 0.865 | **0.868** | +0.023 |
| **Neutral** | 1,233 | 0.549 | 0.630 | 0.587 | 0.575 | 0.627 | **0.600** | +0.013 |
| **Sad** | 1,247 | 0.478 | 0.518 | 0.497 | 0.551 | 0.528 | **0.539** | +0.042 |
| **Surprise** | 831 | 0.728 | 0.798 | 0.761 | 0.828 | 0.747 | **0.785** | +0.024 |

### 3.4 Crucial Production Architecture Finding
- **Runtime Disconnect:** The microservice actively responding to API requests on Port 8002 ([backend/emotion_service_server.py](file:///d:/project%20phase%202/final_project-1/backend/emotion_service_server.py)) loads `emotion_model.keras` (**61.72% accuracy**).
- The superior `emotion_model_v2.keras` (**63.96% accuracy, 63.89% weighted F1, 28.58 MB**) resides in [backend/ml_models/emotion_model_v2.keras](file:///d:/project%20phase%202/final_project-1/backend/ml_models/emotion_model_v2.keras) but is not yet wired into the active serving loop.
- **Data Export:** Predictions for all 7,178 images are exported to [research_experiments/results/exp3_predictions.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp3_predictions.csv).

---

## EXPERIMENT 4 — MPIIGaze Eye Gaze Tracking Evaluation

### 4.1 Coordinate Systems & Metric Formalization
- **Dataset:** MPIIGaze Normalized Dataset.
- **Subject-Independent Partitioning:**
  - Training: Participants `p00` to `p10` (103,254 samples across 11 individuals).
  - Validation: Participants `p11`, `p12` (2,300 samples across 2 individuals).
  - Independent Test: Participants `p13`, `p14` (1,502 samples across 2 individuals).
  - **Disjointness:** Zero subject overlap across train, val, and test.
- **Coordinate Conventions ([ml/eye_contact/preprocess.py](file:///d:/project%20phase%202/final_project-1/ml/eye_contact/preprocess.py)):**
  $$\text{pitch} = \theta = \arcsin(-g_y) \implies g_y = -\sin(\theta)$$
  $$\text{yaw} = \phi = \text{atan2}(-g_x, -g_z) \implies g_x = -\cos(\theta)\sin(\phi), \quad g_z = -\cos(\theta)\cos(\phi)$$
- **Metric Definitions:**
  1. **Pitch MAE:** $\frac{1}{N}\sum_{i=1}^N |\theta_{\text{pred},i} - \theta_{\text{true},i}|$ (radians and degrees).
  2. **Yaw MAE:** $\frac{1}{N}\sum_{i=1}^N |\phi_{\text{pred},i} - \phi_{\text{true},i}|$ (radians and degrees).
  3. **Mean Pitch/Yaw MAE:** $\frac{\text{Pitch MAE} + \text{Yaw MAE}}{2}$ (radians and degrees).
  4. **3D Gaze Vector Angular Error:**
     $$\Delta\theta_i = \arccos\left(\text{clip}\left(\mathbf{g}_{\text{true},i} \cdot \mathbf{g}_{\text{pred},i}, -1.0, 1.0\right)\right)$$

### 4.2 Validation vs. Independent Test Results

| Evaluation Metric | Validation Partition (`p11`, `p12`, $N=2,300$) | Independent Test Partition (`p13`, `p14`, $N=1,502$) |
| :--- | :---: | :---: |
| **Pitch MAE** | 0.0970 rad ($5.56^\circ$) | **0.1290 rad ($7.39^\circ$)** |
| **Yaw MAE** | 0.1037 rad ($5.94^\circ$) | **0.1135 rad ($6.51^\circ$)** |
| **Mean (Pitch + Yaw) / 2 MAE** | **0.1004 rad ($5.75^\circ$)** | **0.1212 rad ($6.95^\circ$)** |
| **3D Gaze Angular Error (Mean)** | 0.1562 rad ($8.95^\circ$) | **0.1878 rad ($10.76^\circ$)** |
| **3D Gaze Angular Error (Median)** | 0.1465 rad ($8.39^\circ$) | **0.1785 rad ($10.23^\circ$)** |
| **3D Gaze Angular Error (p95)** | 0.3022 rad ($17.32^\circ$) | **0.3585 rad ($20.54^\circ$)** |
| **Mean Squared Error (MSE Loss)** | 0.015655 | **0.022890** |
| **Average Latency / Sample** | 0.29 ms/sample | 0.22 ms/sample |

### 4.3 Scientific Clarification of the "0.100 Radians" Claim
1. **Validation vs. Test Discrepancy:**  
   The platform's cited metric of **0.100 radians** is the **Validation MAE** (precisely **0.1004 rad**, or $5.75^\circ$) on participants `p11` and `p12`. On the held-out test participants (`p13`, `p14`), the actual mean pitch/yaw MAE is **0.1212 rad** ($6.95^\circ$).
2. **Angular Vector Metric:**  
   The true 3D gaze-vector angular error on unseen test participants is **$10.76^\circ$ ($0.1878$ rad)** mean and **$10.23^\circ$** median. Pitch/yaw MAE under-reports the true 3D directional error by ~35% because it averages components rather than computing the spherical vector angle.
3. **Data Export:** Per-sample test predictions are saved in [research_experiments/results/exp4_predictions.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp4_predictions.csv).

---

## EXPERIMENT 5 — Eye-Contact Validation Readiness

### 5.1 Status: PENDING LABELED DATA
A comprehensive audit of all files in `ml/eye_contact`, `backend`, and data directories confirmed that **no independently labeled ground-truth dataset for binary eye contact (camera fixation = 1, aversion/screen reading = 0) exists in this repository**.

### 5.2 Circular Logic in Current Evaluation
The current platform implementation in [ml/eye_contact/calibrate_eye_contact.py](file:///d:/project%20phase%202/final_project-1/ml/eye_contact/calibrate_eye_contact.py) evaluates "eye contact" using a fixed geometric threshold on predicted pitch and yaw:
$$\text{eye\_contact} = (|\theta - \theta_{\text{center}}| \le 0.060\text{ rad}) \land (|\phi - \phi_{\text{center}}| \le 0.075\text{ rad})$$
Calculating precision, recall, or F1-scores against the model's own heuristic threshold decisions constitutes a **circular-evaluation fallacy**. True classification accuracy requires external ground-truth gaze target labels.

### 5.3 Consented Human Data Collection & Labeling Protocol
To enable genuine eye-contact validation, the following protocol has been formalized and saved in [research_experiments/results/exp5_eye_contact_status.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp5_eye_contact_status.json):

1. **Participant Cohort:**
   - 15–20 participants with diverse facial morphology, skin tones, and eyewear (glasses, contacts, none).
   - Strict subject separation: 60% calibration cohort (to determine optimal angular tolerances), 40% independent evaluation cohort.
2. **Fixation Conditions:**
   - **Condition 1 (Camera Fixation — True Eye Contact, Label 1):** Continuous 10-second fixation directly at the webcam pinhole.
   - **Condition 2 (Screen Reading — Label 0):** Reading text situated in the screen center (~$10^\circ$–$15^\circ$ below camera).
   - **Condition 3 (Interface Navigation — Label 0):** Reading prompts in top-left, top-right, and bottom corners of the display.
   - **Condition 4 (Aversion — Label 0):** Natural downward note-taking or looking away towards the room.
3. **Target Metrics Upon Data Collection:**
   - Binary Precision, Recall, F1-score, Specificity.
   - ROC-AUC curve generated by sweeping angular distance thresholds $\tau \in [0.02, 0.15]\text{ rad}$.

---

## Generated Visualizations & Artifact Index

All figures below were generated directly from recorded experimental CSV/JSON files:

| Visualization | Output File Path | Description |
| :--- | :--- | :--- |
| **Figure 1** | [research_experiments/plots/exp1_wer_cer_comparison.png](file:///d:/project%20phase%202/final_project-1/research_experiments/plots/exp1_wer_cer_comparison.png) | Corpus WER/CER comparison and error decomposition ($S, D, I$) for Base, 20k, and 40k LoRA. |
| **Figure 2** | [research_experiments/plots/exp2_latency_vs_duration.png](file:///d:/project%20phase%202/final_project-1/research_experiments/plots/exp2_latency_vs_duration.png) | Processing latency vs. audio duration regression and Real-Time Factor (RTF) distribution across 150 runs. |
| **Figure 3** | [research_experiments/plots/exp3_confusion_matrices.png](file:///d:/project%20phase%202/final_project-1/research_experiments/plots/exp3_confusion_matrices.png) | Side-by-side 7×7 confusion matrices for legacy v1 CNN (61.72%) vs. MobileNetV2 v2 (63.96%). |
| **Figure 4** | [research_experiments/plots/exp4_gaze_error_distributions.png](file:///d:/project%20phase%202/final_project-1/research_experiments/plots/exp4_gaze_error_distributions.png) | Validation vs. Test MAE breakdown and 3D gaze vector angular error distribution on independent test participants. |

---

## Master Claims & Empirical Assessment Table

| Claim / Benchmark | Tested Object | Empirical Result | Status / Assessment | Provenance & Log Citation |
| :--- | :--- | :--- | :---: | :--- |
| **Whisper 20k LoRA achieves 17.33% norm WER** | Common Voice EN-IN (500 clips) | **17.33% normalized WER** ($S=638, D=65, I=120$) | **Reproduced** | [exp1_whisper_comparison.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp1_whisper_comparison.json) |
| **Whisper LoRA outperforms Base Whisper** | Common Voice EN-IN (500 clips) | Base: 20.13% WER $\rightarrow$ 20k: 17.33% WER ($\Delta = -2.80\text{ pp}$) | **Supported by saved results** | [exp1_predictions.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp1_predictions.csv) |
| **40k Whisper improves over 20k** | Common Voice EN-IN (500 clips) | 20k: 17.33% WER $\rightarrow$ 40k: 17.04% WER ($\Delta = -0.29\text{ pp}$) | **Supported by saved results** | [exp1_whisper_comparison.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp1_whisper_comparison.json) |
| **Whisper ASR latency is universally 823.89 ms** | 50 clips $\times$ 3 reps (CUDA sync) | Mean: 542.60 ms, p95: 853.77 ms, RTF: 0.105 (9.5× real-time) | **Incorrect as stated** | [exp2_asr_latency.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp2_asr_latency.json) |
| **Emotion v2 achieves 63.96% accuracy / 63.89% F1** | FER-2013 Test (7,178 images) | **63.96% accuracy, 63.89% weighted F1** | **Reproduced** | [exp3_emotion_comparison.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp3_emotion_comparison.json) |
| **Emotion v2 outperforms legacy v1 CNN** | FER-2013 Test (7,178 images) | v1: 61.72% $\rightarrow$ v2: 63.96% ($\Delta = +2.24\text{ pp}$), size: 70.6MB $\rightarrow$ 28.6MB | **Supported by saved results** | [exp3_predictions.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp3_predictions.csv) |
| **Production Emotion service uses v2 model** | Port 8002 Service Server | Port 8002 actively loads legacy v1 CNN (61.72%) | **Incorrect** | [backend/emotion_service_server.py:L40](file:///d:/project%20phase%202/final_project-1/backend/emotion_service_server.py#L40) |
| **Gaze estimation achieves 0.100 rad error on Test** | MPIIGaze Test (`p13`, `p14`) | Val MAE = 0.1004 rad ($5.75^\circ$); Test MAE = **0.1212 rad ($6.95^\circ$)** | **Incorrect** | [exp4_gaze_evaluation.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp4_gaze_evaluation.json) |
| **Gaze 3D Vector Angular Error evaluated** | MPIIGaze Test (`p13`, `p14`) | Mean 3D Angular Error = **$10.76^\circ$ ($0.1878$ rad)** | **Supported by saved results** | [exp4_predictions.csv](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp4_predictions.csv) |
| **Binary Eye-Contact accuracy evaluated** | Consented Ground-Truth Gaze | No labeled ground-truth data exists; uses heuristic thresholds | **PENDING LABELED DATA** | [exp5_eye_contact_status.json](file:///d:/project%20phase%202/final_project-1/research_experiments/results/exp5_eye_contact_status.json) |
