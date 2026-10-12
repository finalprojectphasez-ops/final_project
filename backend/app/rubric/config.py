"""
Versioned Rubric Configuration for PreMock AI 100-Mark Assessment.
Rubric Version: interview_practice_100_v1
"""

from typing import Dict, Any, List

RUBRIC_VERSION = "interview_practice_100_v1"

RUBRIC_CRITERIA: Dict[str, Dict[str, Any]] = {
    "technical_knowledge": {
        "id": "technical_knowledge",
        "name": "Technical / job-role knowledge",
        "max_marks": 30.0,
        "description": "Assesses foundational and role-specific technical mechanisms, concepts, and domain competence.",
        "anchors": {
            0: "Fundamental misconception or no substantive explanation.",
            1: "Recognizes terms but makes major errors.",
            2: "Partly correct with important gaps.",
            3: "Correct concepts and mechanisms for the selected level.",
            4: "Accurate explanation with relevant distinctions, boundaries or counterexamples."
        }
    },
    "problem_solving": {
        "id": "problem_solving",
        "name": "Problem-solving and reasoning",
        "max_marks": 20.0,
        "description": "Assesses logical approach, structured reasoning, trade-off analysis, and failure mode verification.",
        "anchors": {
            0: "No workable approach.",
            1: "Guesses without justification.",
            2: "Plausible approach with significant gaps.",
            3: "Coherent steps, justified decisions and verification.",
            4: "Compares alternatives, explains tradeoffs and checks relevant failure cases."
        }
    },
    "practical_application": {
        "id": "practical_application",
        "name": "Practical application and examples",
        "max_marks": 15.0,
        "description": "Assesses concrete implementation experience, personal/coursework projects, or well-reasoned hypothetical exercises.",
        "anchors": {
            0: "No usable example.",
            1: "Generic claims.",
            2: "Relevant example with unclear implementation or outcome.",
            3: "Concrete actions and a plausible outcome or verification method.",
            4: "Specific decisions, contribution, checks and limitations. Accepts coursework, personal projects, or clearly identified hypothetical exercises."
        }
    },
    "relevance_completeness": {
        "id": "relevance_completeness",
        "name": "Relevance and completeness",
        "max_marks": 10.0,
        "description": "Assesses direct responsiveness to the interview prompt and thoroughness of coverage.",
        "anchors": {
            0: "Does not address the question.",
            1: "Addresses peripheral points.",
            2: "Addresses the main request but misses important parts.",
            3: "Covers the important requested parts.",
            4: "Complete, focused and appropriately prioritized."
        }
    },
    "communication_clarity": {
        "id": "communication_clarity",
        "name": "Communication clarity",
        "max_marks": 10.0,
        "description": "Assesses organization, terminological precision, and coherent articulation.",
        "anchors": {
            0: "Explanation remains uninterpretable with usable evidence.",
            1: "Disconnected ideas.",
            2: "Understandable main point with organizational gaps.",
            3: "Clear organization and terminology.",
            4: "Precise explanation supported by helpful examples or definitions."
        }
    },
    "followup_reflection": {
        "id": "followup_reflection",
        "name": "Follow-up response and reflection",
        "max_marks": 10.0,
        "description": "Assesses engagement with probes, willingness to clarify or correct reasoning under challenge.",
        "anchors": {
            0: "Does not engage with the probe.",
            1: "Repeats the original answer.",
            2: "Addresses part of the probe.",
            3: "Addresses it and clarifies or corrects reasoning.",
            4: "Incorporates it coherently and supports the revised reasoning with an example or check."
        }
    },
    "spoken_delivery": {
        "id": "spoken_delivery",
        "name": "Spoken delivery and intelligibility",
        "max_marks": 5.0,
        "description": "Assesses audibility, pacing, and verbal intelligibility from usable audio recordings.",
        "anchors": {
            0: "Unintelligible despite a usable recording and clarification opportunity.",
            1: "Delivery frequently obscures meaning.",
            2: "Mostly understandable with recurring interference.",
            3: "Understandable pacing and audibility.",
            4: "Consistently easy to follow with useful pauses or emphasis."
        }
    }
}

TOTAL_MAX_MARKS = sum(c["max_marks"] for c in RUBRIC_CRITERIA.values())
if TOTAL_MAX_MARKS != 100.0:
    raise ValueError(f"Rubric configuration error: total maximum marks must equal 100, got {TOTAL_MAX_MARKS}")

# Ordering for consistent display and reports
ORDERED_CRITERIA_KEYS: List[str] = [
    "technical_knowledge",
    "problem_solving",
    "practical_application",
    "relevance_completeness",
    "communication_clarity",
    "followup_reflection",
    "spoken_delivery"
]

# Mapping of interview group types to criteria they can fairly assess
GROUP_ELIGIBILITY_RULES: Dict[str, List[str]] = {
    "intro": [
        "communication_clarity",
        "relevance_completeness"
    ],
    "technical": [
        "technical_knowledge",
        "problem_solving",
        "practical_application",
        "relevance_completeness",
        "communication_clarity",
        "followup_reflection"
    ],
    "practical_example": [
        "practical_application",
        "problem_solving",
        "technical_knowledge",
        "relevance_completeness",
        "communication_clarity"
    ],
    "softskill": [
        "problem_solving",
        "practical_application",
        "communication_clarity",
        "relevance_completeness",
        "followup_reflection"
    ]
}
