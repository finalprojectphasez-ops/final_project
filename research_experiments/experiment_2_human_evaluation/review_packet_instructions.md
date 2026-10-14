# Human Reviewer Instructions: Interview Rubric Evaluation (Pilot Study)

**Rubric Version:** `interview_practice_100_v1`  
**Evaluation Scope:** 35 Anonymized Candidate Responses across 6 Professional Roles  
**Study Design:** Double-Blinded Independent Review (Automated scores hidden)

---

## 1. General Instructions
1. You have been provided with `review_scoring_template_reviewer1.csv` (or reviewer 2).
2. For each candidate response, evaluate the answer strictly against the interview question and assigned role/difficulty.
3. Assign an **integer anchor from 0 to 4** for each eligible criterion.
4. Do NOT calculate percentages or overall weighted marks; enter only the integer anchor (0, 1, 2, 3, or 4).
5. For text-only evaluations, `spoken_delivery` is marked `N/A (Text-Only)` and will be excluded from text-based agreement calculations.

---

## 2. Authoritative 0–4 Anchor Descriptions

### Criterion 1: `technical_knowledge` (Max Marks: 30.0)
- **Anchor 0:** Fundamental misconception or no substantive explanation.
- **Anchor 1:** Recognizes terms superficially without core technical mechanisms.
- **Anchor 2:** Partly correct with important gaps in implementation mechanisms.
- **Anchor 3:** Correct technical concepts and mechanisms for the selected seniority level.
- **Anchor 4:** Accurate explanation with relevant distinctions, boundaries or trade-offs.

### Criterion 2: `problem_solving` (Max Marks: 20.0)
- **Anchor 0:** No workable approach presented.
- **Anchor 1:** Guesses without logical justification.
- **Anchor 2:** Plausible approach with significant verification gaps.
- **Anchor 3:** Coherent steps, justified decisions and verification.
- **Anchor 4:** Compares alternatives, explains trade-offs and checks relevant failure cases.

### Criterion 3: `practical_application` (Max Marks: 15.0)
- **Anchor 0:** No usable example.
- **Anchor 1:** Generic claims without concrete actions.
- **Anchor 2:** Relevant example with unclear implementation or outcome.
- **Anchor 3:** Concrete actions and a plausible outcome or verification method.
- **Anchor 4:** Specific decisions, contribution, checks and limitations (accepts coursework or personal projects).

### Criterion 4: `relevance_completeness` (Max Marks: 10.0)
- **Anchor 0:** Does not address the question.
- **Anchor 1:** Addresses peripheral points.
- **Anchor 2:** Addresses main request but misses important parts.
- **Anchor 3:** Covers important requested components.
- **Anchor 4:** Complete, focused and appropriately prioritized.

### Criterion 5: `communication_clarity` (Max Marks: 10.0)
- **Anchor 0:** Explanation remains uninterpretable with usable evidence.
- **Anchor 1:** Disconnected ideas.
- **Anchor 2:** Understandable main point with organizational gaps.
- **Anchor 3:** Clear organization and terminology.
- **Anchor 4:** Precise explanation supported by helpful examples or definitions.

### Criterion 6: `followup_reflection` (Max Marks: 10.0)
- **Anchor 0:** Does not engage with the probe.
- **Anchor 1:** Repeats the original answer without new depth.
- **Anchor 2:** Addresses part of the probe.
- **Anchor 3:** Addresses it and clarifies or corrects reasoning.
- **Anchor 4:** Incorporates it coherently and supports revised reasoning with an example or check.

---

## 3. Data Flow
1. Complete your column entries independently without consulting Reviewer 2.
2. Save your CSV as `review_scoring_template_reviewerX.csv`.
3. Run `python analyze_human_rubric_agreement.py` to compute inter-rater Cohen's kappa and MAE.
