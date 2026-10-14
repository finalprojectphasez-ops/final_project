# 100-Mark Interview Assessment Rubric (`interview_practice_100_v1`)

## Overview

The PreMock AI platform implements a deterministic, 100-mark assessment rubric (`interview_practice_100_v1`) powered exclusively by **local inference** (zero paid or external AI APIs). The rubric evaluates candidate competence across 7 criteria with strictly defined scoring anchors (0–4), topic group aggregation, exact answer quote verification, and complete isolation of vision/coaching signals from marks.

---

## 1. Versioned Rubric Configuration

### Criteria & Weight Distribution (Total: 100 Marks)

| Criterion ID | Criterion Name | Max Marks | Description |
|---|---|---:|---|
| `technical_knowledge` | Technical / job-role knowledge | 30 | Foundational & role-specific mechanisms, concepts, and domain competence |
| `problem_solving` | Problem-solving and reasoning | 20 | Logical steps, structured reasoning, trade-off analysis, and failure checking |
| `practical_application` | Practical application and examples | 15 | Concrete project experience, coursework, or clearly reasoned hypothetical exercises |
| `relevance_completeness` | Relevance and completeness | 10 | Direct responsiveness to prompt and completeness of topic coverage |
| `communication_clarity` | Communication clarity | 10 | Structured organization, terminology precision, and coherent articulation |
| `followup_reflection` | Follow-up response and reflection | 10 | Engagement with probes and clarification/correction of reasoning under challenge |
| `spoken_delivery` | Spoken delivery and intelligibility | 5 | Audibility, pacing, and verbal intelligibility from usable audio recordings |
| **TOTAL** | | **100** | |

### Criterion-Specific Scoring Anchors (0 to 4)

- **Technical Knowledge (0–4)**:
  - `0`: Fundamental misconception or no substantive explanation.
  - `1`: Recognizes terms but makes major errors.
  - `2`: Partly correct with important gaps in mechanisms.
  - `3`: Correct concepts and mechanisms for the selected role and level.
  - `4`: Accurate explanation with relevant distinctions, boundaries or counterexamples.

- **Problem-Solving (0–4)**:
  - `0`: No workable approach.
  - `1`: Guesses without justification.
  - `2`: Plausible approach with significant gaps in verification.
  - `3`: Coherent steps, justified decisions and verification.
  - `4`: Compares alternatives, explains tradeoffs and checks relevant failure cases.

- **Practical Application (0–4)**:
  - `0`: No usable example.
  - `1`: Generic claims without concrete actions or verified outcome.
  - `2`: Relevant example with unclear implementation or outcome.
  - `3`: Concrete actions and a plausible outcome or verification method.
  - `4`: Specific decisions, contribution, checks and limitations. Accepts coursework, personal projects, or clearly identified hypothetical exercises.

- **Relevance / Completeness (0–4)**:
  - `0`: Does not address the question.
  - `1`: Addresses peripheral points.
  - `2`: Addresses main request but misses important parts.
  - `3`: Covers the important requested parts.
  - `4`: Complete, focused and appropriately prioritized.

- **Communication Clarity (0–4)**:
  - `0`: Explanation remains uninterpretable with usable evidence.
  - `1`: Disconnected ideas.
  - `2`: Understandable main point with organizational gaps.
  - `3`: Clear organization and terminology.
  - `4`: Precise explanation supported by helpful examples or definitions.

- **Follow-up Reflection (0–4)**:
  - `0`: Does not engage with the probe.
  - `1`: Repeats the original answer without new depth.
  - `2`: Addresses part of the probe.
  - `3`: Addresses probe and clarifies or corrects reasoning.
  - `4`: Incorporates probe coherently and supports revised reasoning with trade-offs or checks.

- **Spoken Delivery (0–4)**:
  - `0`: Unintelligible despite a usable recording and clarification opportunity.
  - `1`: Delivery frequently obscures meaning.
  - `2`: Mostly understandable with recurring interference.
  - `3`: Understandable pacing and audibility.
  - `4`: Consistently easy to follow with useful pauses or emphasis.

---

## 2. Deterministic Calculation Rules

Backend code strictly handles arithmetic; model proposals are limited to ratings (0–4) and evidence:

$$\text{criterion\_marks} = \frac{\text{criterion\_rating}}{4.0} \times \text{maximum\_marks}$$

The overall score is computed once at interview level by summing criterion marks:

$$\text{overall\_score} = \sum \text{criterion\_marks}$$

### Input Validation
- Criteria IDs must match `RUBRIC_CRITERIA`.
- Ratings must be finite numbers (`int` or `float`) between `0.0` and `4.0`, or `None` if unassessed.
- Python booleans (`True`/`False`), `NaN`, $\pm\infty$, non-numeric values, and out-of-range ratings are strictly rejected with `RubricValidationError`.

---

## 3. Interview Aggregation & Topic Group Weighting

1. **Topic Grouping**: Each main question and all subsequent follow-up probes belong to a single **Topic Group**.
2. **Equal Group Weight**: Follow-up count **does not increase** a topic's voting weight. For any criterion, the interview-wide rating is the arithmetic mean across all groups eligible to assess that criterion:
   $$\text{criterion\_rating} = \frac{1}{N_{\text{eligible groups}}} \sum_{g=1}^{N_{\text{eligible groups}}} \text{group\_rating}_g$$
3. **Self-Corrections**: When candidates revise their answer during probes (`"actually, to correct..."`), both original and revised utterances are preserved in topic group history.

---

## 4. Partial Assessments & Evidence Safeguards

- **Complete Assessment**: Only awarded when all 7 criteria (including `spoken_delivery`) have usable evidence. `total_score_100` is returned.
- **Partial Assessment**: If any criterion is missing (e.g. `spoken_delivery` when audio classifier was not run), `total_score_100` **must remain null**.
  - A provisional score is calculated:
    $$\text{provisional\_normalized\_100} = \frac{\text{assessed\_score}}{\text{assessed\_maximum}} \times 100$$
  - Clearly displayed as **Provisional** alongside `coverage_percent` (e.g. 95% coverage).
  - *An audio-missing assessment out of 95 is never presented as a complete score out of 100.*
- **Unassessed**: When all criteria are null, `total_score_100 = null`, `provisional_normalized_100 = null`, and `coverage_percent = 0.0`.

---

## 5. Separation of Audiovisual Coaching Data

- Proctoring signals (eye contact %, face presence %, expression distribution, head posture) are kept **strictly outside the 100 marks**.
- Facial emotion and gaze classifier probabilities do not alter criterion marks or penalize candidates.
- Evaluators do not penalize accent, pitch, appearance, or filler word counts as proxies for technical competence.

---

## 6. Verifiable Evidence & Human Audit Export

- All proposed text evidence is checked against candidate transcripts using exact substring matching. Quotes not present in candidate answers trigger `requires_review`.
- Endpoints:
  - `GET /api/rubric/config`: Returns active rubric definition, weights, and anchors.
  - `POST /api/rubric/assess`: Evaluates session turns using local model inference.
  - `POST /api/rubric/manual-review`: Allows human reviewers to submit overrides (e.g. rating `spoken_delivery`).
  - `GET /api/rubric/export/{session_id}?format=json`: Exports full transcript, verifiable quote evidence, and marks for provenance audit.
  - `GET /api/rubric/export/{session_id}?format=csv`: Exports tabular criteria audit breakdown.

---

## 7. Dataset Limitations & Provenance Notice

> **Important**: The pre-existing 10,000-row interview dataset contains synthetic 10-point generation examples and does **not** contain human-reviewed ground truth targets for this 100-mark rubric. Synthetic 10-point rows must **not** be scaled by 10 to simulate 100-mark labels. Full provenance is recorded on every session so human auditors can review, calibrate, and export genuine assessment evidence.
