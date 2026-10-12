"""
Persistent Session Manager for PreMock AI.
Enforces session rules, topic order, turn counters, duplicate submission prevention,
private expected_points storage, and disk persistence under backend/data/sessions/.
"""

import os
import time
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

from app.models.schemas import (
    ProfessionalProfile,
    InterviewQuestionInternal,
    CandidateQuestionResponse,
    TurnSubmitResponse,
    InterviewSessionResponse
)
from app.services.local_interview_model import (
    local_interview_model,
    normalize_role,
    normalize_difficulty
)

logger = logging.getLogger("uvicorn.error")

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


class SessionManager:
    """
    Manages interview session lifecycle, state machines, and disk persistence.
    """

    def __init__(self, sessions_dir: str = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _session_file_path(self, session_id: str) -> str:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.sessions_dir, f"{safe_id}.json")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._session_file_path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read session %s: %s", session_id, e)
            return None

    def save_session(self, session_data: Dict[str, Any]) -> None:
        session_id = session_data["session_id"]
        path = self._session_file_path(session_id)
        session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            logger.error("Failed to write session %s: %s", session_id, e)

    def create_session(
        self,
        session_id: str,
        role: str,
        difficulty: str,
        duration_minutes: int = 30,
        resume_profile: Optional[ProfessionalProfile] = None,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a new interview session.
        Selected role and difficulty remain strictly authoritative.
        Builds topic plan and generates the first main question.
        Timer starts now at launch.
        """
        canonical_role_key, taxonomy = normalize_role(role)
        norm_diff = normalize_difficulty(difficulty)
        duration_val = duration_minutes if duration_minutes in (15, 30, 45) else 30

        # Topic plan
        topic_plan = local_interview_model.build_topic_plan(
            role=role,
            difficulty=norm_diff,
            duration_minutes=duration_val,
            resume_profile=resume_profile
        )

        now_ts = time.time()
        deadline_ts = now_ts + (duration_val * 60)

        # Generate first question
        first_topic = topic_plan[0]["topic"] if topic_plan else "Role Fundamentals"
        first_q = local_interview_model.generate_main_question(
            role=role,
            difficulty=norm_diff,
            required_topic=first_topic,
            resume_profile=resume_profile,
            history=[]
        )

        session_data = {
            "session_id": session_id,
            "role": taxonomy["display_name"],
            "role_key": canonical_role_key,
            "difficulty": norm_diff,
            "duration_minutes": duration_val,
            "start_timestamp": now_ts,
            "deadline_timestamp": deadline_ts,
            "status": "active",
            "session_version": 1,
            "current_turn": 1,
            "current_topic_index": 0,
            "followups_used": 0,
            "max_followups_per_topic": 2,
            "topic_plan": topic_plan,
            "current_question": first_q.model_dump(),
            "history": [],
            "resume_profile": resume_profile.model_dump() if resume_profile else None,
            "resume_text": resume_text,
            "job_description": job_description,
            "last_submission_hash": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        self.save_session(session_data)
        return session_data

    def submit_turn(
        self,
        session_id: str,
        answer: str,
        turn_id: Optional[str] = None,
        next_main_difficulty: Optional[str] = None
    ) -> TurnSubmitResponse:
        """
        Submits candidate answer for the current question.
        Enforces:
        - Duplicate answer rejection / idempotency
        - Session deadline priority
        - Follow-up limits (max 2 per topic)
        - Follow-up counter reset ONLY when advancing to new main topic
        - Private expected_points storage (never sent to candidate)
        """
        session = self.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        if session["status"] == "completed":
            return TurnSubmitResponse(
                action="end",
                next_question=None,
                session_id=session_id,
                turn_index=session["current_turn"],
                current_topic_index=session["current_topic_index"],
                followups_used=session["followups_used"],
                remaining_topics_count=0,
                is_complete=True,
                deadline_expired=False,
                evaluation=None
            )

        clean_ans = (answer or "").strip()
        if not clean_ans:
            raise HTTPException(status_code=400, detail="Answer cannot be empty.")

        # Duplicate submission protection:
        # Prevent rapid double-clicks or repeated submission of the identical answer within 15 seconds
        last_ans = session.get("last_submitted_answer", "")
        last_ts = session.get("last_submitted_timestamp", 0)
        last_turn_id = session.get("last_processed_turn_id")

        if turn_id and turn_id == last_turn_id:
            raise HTTPException(
                status_code=409,
                detail="Duplicate submission detected. This turn has already been processed."
            )

        if last_ans and clean_ans.lower() == last_ans.lower() and (time.time() - last_ts < 15.0):
            raise HTTPException(
                status_code=409,
                detail="Duplicate submission detected. This answer was already submitted."
            )

        current_q_data = session["current_question"]
        current_q = InterviewQuestionInternal(**current_q_data)

        # Check deadline
        now_ts = time.time()
        deadline_expired = now_ts >= session["deadline_timestamp"]

        # Turn policy inputs
        current_topic_idx = session["current_topic_index"]
        topic_plan = session["topic_plan"]
        remaining_topics = topic_plan[current_topic_idx + 1:] if current_topic_idx + 1 < len(topic_plan) else []
        followups_used = session["followups_used"]
        max_followups = session.get("max_followups_per_topic", 2)

        resume_profile = None
        if session.get("resume_profile"):
            try:
                resume_profile = ProfessionalProfile(**session["resume_profile"])
            except Exception:
                pass

        # Determine allowed actions
        allowed_actions = []
        if deadline_expired or (not remaining_topics and followups_used >= max_followups):
            allowed_actions = ["end"]
        elif followups_used >= max_followups:
            allowed_actions = ["next_topic", "end"]
        else:
            allowed_actions = ["follow_up", "clarify", "next_topic", "end"]

        # Run local model follow-up generator
        action, next_q_internal, turn_meta = local_interview_model.generate_followup_turn(
            role=session["role"],
            difficulty=session["difficulty"],
            current_question=current_q,
            latest_answer=clean_ans,
            conversation_history=session["history"],
            remaining_topics=remaining_topics,
            followups_used=followups_used,
            max_followups_per_topic=max_followups,
            allowed_actions=allowed_actions,
            deadline_expired=deadline_expired,
            next_main_difficulty=next_main_difficulty,
            resume_profile=resume_profile
        )

        # Candidate answer evaluation against private expected points
        words = len(clean_ans.split())
        is_non_answer = any(kw in clean_ans.lower() for kw in ["don't know", "dont know", "no idea", "skip", "not sure"])
        matched_points = [ep for ep in current_q.expected_points if any(w.lower() in clean_ans.lower() for w in ep.split() if len(w) > 3)]

        if is_non_answer:
            eval_score = 25
            tech_depth = 15
            relevance = 20
            clarity = 60
            comp = 15
        else:
            coverage = len(matched_points) / max(1, len(current_q.expected_points))
            base_score = 50 + int(coverage * 35) + min(15, words // 5)
            eval_score = min(95, max(30, base_score))
            tech_depth = min(95, max(30, 45 + int(coverage * 40)))
            relevance = min(95, max(30, 50 + int(coverage * 40)))
            clarity = min(95, max(40, 60 + min(30, words // 3)))
            comp = min(95, max(20, int(coverage * 90) + 10))

        evaluation = {
            "score": eval_score,
            "relevance": relevance,
            "technical_depth": tech_depth,
            "clarity": clarity,
            "completeness": comp,
            "matched_expected_points_count": len(matched_points),
            "strengths": ["Clear articulation", "Addressed question requirements"] if not is_non_answer else ["Honest admission of knowledge gap"],
            "improvements": ["Elaborate on production tradeoffs", "Provide architectural edge cases"] if not is_non_answer else ["Review foundational concepts"],
            "evaluation": f"Turn answered covering {len(matched_points)}/{len(current_q.expected_points)} key criteria."
        }

        # Record completed turn in history (including private expected_points)
        turn_record = {
            "turn_index": session["current_turn"],
            "topic": current_q.topic,
            "question": current_q.question,
            "kind": current_q.kind,
            "difficulty": current_q.difficulty,
            "expected_points": current_q.expected_points,  # Private on backend
            "review_status": current_q.review_status,
            "candidate_answer": clean_ans,
            "evaluation": evaluation,
            "timestamp": now_ts
        }
        session["history"].append(turn_record)

        # Counter management & state transitions
        if action == "next_topic":
            session["current_topic_index"] += 1
            session["followups_used"] = 0  # CRITICAL INVARIANT: Resets to 0 only on new main topic!
            session["current_question"] = next_q_internal.model_dump() if next_q_internal else None
        elif action in ("follow_up", "clarify"):
            session["followups_used"] += 1
            session["current_question"] = next_q_internal.model_dump() if next_q_internal else None
        elif action == "end":
            session["status"] = "completed"
            session["current_question"] = None

        session["last_submitted_answer"] = clean_ans
        session["last_submitted_timestamp"] = now_ts
        session["last_processed_turn_id"] = turn_id
        session["session_version"] += 1
        session["current_turn"] += 1

        self.save_session(session)

        # Project candidate response: explicitly strip expected_points!
        candidate_next_q = None
        if next_q_internal:
            candidate_next_q = CandidateQuestionResponse(
                question=next_q_internal.question,
                topic=next_q_internal.topic,
                kind=next_q_internal.kind,
                difficulty=next_q_internal.difficulty
            )

        return TurnSubmitResponse(
            action=action,
            next_question=candidate_next_q,
            session_id=session_id,
            turn_index=session["current_turn"],
            current_topic_index=session["current_topic_index"],
            followups_used=session["followups_used"],
            remaining_topics_count=len(remaining_topics),
            is_complete=(action == "end" or session["status"] == "completed"),
            deadline_expired=deadline_expired,
            evaluation=evaluation
        )

    def get_candidate_session_view(self, session_id: str) -> Dict[str, Any]:
        """
        Returns a clean view of the session state for candidate resume/reload.
        Strips all private expected_points from questions and history!
        """
        session = self.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        # Clean current question
        candidate_q = None
        if session.get("current_question"):
            cq = session["current_question"]
            candidate_q = {
                "question": cq["question"],
                "topic": cq["topic"],
                "kind": cq["kind"],
                "difficulty": cq["difficulty"]
            }

        # Clean history
        candidate_history = []
        for h in session.get("history", []):
            candidate_history.append({
                "turn_index": h["turn_index"],
                "topic": h["topic"],
                "question": h["question"],
                "kind": h["kind"],
                "difficulty": h["difficulty"],
                "candidate_answer": h["candidate_answer"],
                "evaluation": h.get("evaluation")
            })

        return {
            "session_id": session["session_id"],
            "role": session["role"],
            "difficulty": session["difficulty"],
            "duration_minutes": session["duration_minutes"],
            "status": session["status"],
            "session_version": session["session_version"],
            "current_turn": session["current_turn"],
            "current_topic_index": session["current_topic_index"],
            "followups_used": session["followups_used"],
            "planned_topics": [t["topic"] for t in session.get("topic_plan", [])],
            "deadline_timestamp": session["deadline_timestamp"],
            "current_question": candidate_q,
            "history": candidate_history
        }


# Global singleton manager
session_manager = SessionManager()
