"""
Interview Turn and Topic Group Aggregator for 100-Mark Rubric.
Treats each main question and its follow-ups as a single topic group,
ensuring equal group weighting without multiplying weight by follow-up counts.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from app.rubric.config import GROUP_ELIGIBILITY_RULES, RUBRIC_CRITERIA


@dataclass
class TurnItem:
    turn_index: int
    question: str
    answer: str
    phase: str = "technical"
    is_followup: bool = False
    parent_topic_id: Optional[str] = None
    audio_present: bool = False


@dataclass
class TopicGroup:
    group_id: str
    title: str
    phase: str
    main_question: str
    main_answer: str
    followups: List[Dict[str, str]] = field(default_factory=list)
    revisions: List[Dict[str, str]] = field(default_factory=list)
    eligible_criteria: List[str] = field(default_factory=list)
    has_audio: bool = False

    def all_answers_text(self) -> str:
        """Returns combined text of all candidate utterances in this topic group."""
        texts = [self.main_answer]
        for f in self.followups:
            if f.get("answer"):
                texts.append(f["answer"])
        return "\n".join(texts)


def classify_group_phase(question: str, turn_phase: str) -> str:
    """Classifies question group into rubric eligibility profile."""
    q_lower = question.lower()
    if turn_phase == "intro" or "introduce yourself" in q_lower or "tell me about yourself" in q_lower:
        return "intro"
    if turn_phase == "softskill" or any(w in q_lower for w in ["deadline", "conflict", "disagreement", "teamwork", "pressure"]):
        return "softskill"
    if any(w in q_lower for w in ["example", "project you built", "walk me through a major project", "practical", "codebase", "hands-on"]):
        return "practical_example"
    return "technical"


def build_topic_groups_from_history(turns: List[Dict[str, Any]]) -> List[TopicGroup]:
    """
    Groups raw interview turns into structured Topic Groups.
    A main question and all subsequent follow-ups belong to the same group.
    """
    if not turns:
        return []

    groups: List[TopicGroup] = []
    current_group: Optional[TopicGroup] = None
    group_counter = 1

    for turn in turns:
        q = (turn.get("question") or "").strip()
        a = (turn.get("answer") or "").strip()
        phase = turn.get("phase") or "technical"
        is_followup = turn.get("is_followup", False) or turn.get("follow_up_needed", False)

        # Self-correction detection to preserve original and revised answers
        is_revision = any(marker in a.lower() for marker in [
            "actually, to correct", "let me correct", "i made a mistake",
            "to clarify my earlier", "on second thought", "correction:"
        ])

        # New group condition: not marked as follow-up, or current_group is None
        # or explicit question transition
        if not is_followup or current_group is None:
            classified_phase = classify_group_phase(q, phase)
            eligible = GROUP_ELIGIBILITY_RULES.get(classified_phase, GROUP_ELIGIBILITY_RULES["technical"])

            current_group = TopicGroup(
                group_id=f"topic_{group_counter}",
                title=f"Topic {group_counter}: {classified_phase.replace('_', ' ').title()}",
                phase=classified_phase,
                main_question=q,
                main_answer=a,
                followups=[],
                revisions=[{"question": q, "revised_answer": a}] if is_revision else [],
                eligible_criteria=list(eligible),
                has_audio=bool(turn.get("audio_present", False))
            )
            groups.append(current_group)
            group_counter += 1
        else:
            # Append follow-up probe and answer to the active topic group
            current_group.followups.append({"question": q, "answer": a})
            if is_revision:
                current_group.revisions.append({"question": q, "revised_answer": a})
            if turn.get("audio_present"):
                current_group.has_audio = True

    return groups


def aggregate_criterion_ratings_across_groups(
    group_assessments: List[Dict[str, Any]],
    spoken_delivery_rating: Optional[float] = None
) -> Dict[str, Optional[float]]:
    """
    Averages each criterion's rating across its eligible groups with EQUAL group weight.
    Crucial Rule: Follow-up counts do NOT increase a topic's voting weight.
    """
    criterion_group_ratings: Dict[str, List[float]] = {k: [] for k in RUBRIC_CRITERIA.keys()}

    for g_ass in group_assessments:
        eligible_set: Set[str] = set(g_ass.get("eligible_criteria", []))
        ratings: Dict[str, Any] = g_ass.get("ratings", {})

        for crit_id, val in ratings.items():
            if crit_id in eligible_set and val is not None:
                # Add group-level rating
                criterion_group_ratings[crit_id].append(float(val))

    final_ratings: Dict[str, Optional[float]] = {}
    for crit_id in RUBRIC_CRITERIA.keys():
        if crit_id == "spoken_delivery":
            # Spoken delivery is assessed interview-wide from audio evidence or manual review
            final_ratings[crit_id] = spoken_delivery_rating
        else:
            ratings_list = criterion_group_ratings.get(crit_id, [])
            if ratings_list:
                # Equal group-weighted arithmetic average
                final_ratings[crit_id] = sum(ratings_list) / len(ratings_list)
            else:
                final_ratings[crit_id] = None

    return final_ratings
