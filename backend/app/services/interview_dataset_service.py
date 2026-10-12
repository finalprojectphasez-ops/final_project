import os
import csv
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class InterviewDatasetService:
    def __init__(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "interview_dataset.csv")
        self.questions_by_role: Dict[str, List[Dict[str, Any]]] = {}
        self.followups_by_role: Dict[str, List[Dict[str, Any]]] = {}
        self.loaded = False
        self._load_dataset()

    def _load_dataset(self):
        if not os.path.exists(self.csv_path):
            logger.info("interview_dataset.csv not found at %s. Skipping in-memory indexing.", self.csv_path)
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task = row.get("task")
                    role = (row.get("job_role") or "").lower().strip()
                    target_str = row.get("target_json")
                    if not target_str:
                        continue

                    try:
                        target_json = json.loads(target_str)
                    except Exception:
                        continue

                    item = {
                        "job_role": row.get("job_role"),
                        "topic": row.get("topic"),
                        "difficulty": row.get("difficulty"),
                        "target": target_json
                    }

                    if task == "role_question":
                        self.questions_by_role.setdefault(role, []).append(item)
                    elif task == "followup":
                        self.followups_by_role.setdefault(role, []).append(item)

            self.loaded = True
            logger.info(
                "Loaded Interview Dataset: %d role_question roles, %d followup roles.",
                len(self.questions_by_role),
                len(self.followups_by_role)
            )
        except Exception as e:
            logger.error("Failed to load interview dataset: %s", e)

    def find_question_exemplars(self, job_role: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Finds matching questions from the dataset for few-shot prompt injection."""
        if not self.loaded:
            return []

        clean_role = (job_role or "").lower().strip()
        # Exact match first
        matches = self.questions_by_role.get(clean_role, [])
        if not matches:
            # Substring match (e.g. 'developer', 'engineer', 'frontend')
            for r, items in self.questions_by_role.items():
                if any(word in r for word in clean_role.split() if len(word) > 3):
                    matches.extend(items)
                    if len(matches) >= limit * 2:
                        break

        # Fallback to any questions
        if not matches:
            for items in self.questions_by_role.values():
                matches.extend(items[:limit])
                if len(matches) >= limit:
                    break

        return matches[:limit]

    def find_followup_exemplars(self, job_role: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Finds matching follow-ups from the dataset for few-shot prompt injection."""
        if not self.loaded:
            return []

        clean_role = (job_role or "").lower().strip()
        matches = self.followups_by_role.get(clean_role, [])
        if not matches:
            for r, items in self.followups_by_role.items():
                if any(word in r for word in clean_role.split() if len(word) > 3):
                    matches.extend(items)
                    if len(matches) >= limit * 2:
                        break

        if not matches:
            for items in self.followups_by_role.values():
                matches.extend(items[:limit])
                if len(matches) >= limit:
                    break

        return matches[:limit]

    def get_intro_question(self) -> str:
        """Part 1: Self-introduction question."""
        return (
            "Welcome to your interview! To start off, please introduce yourself, "
            "tell me about your background, and provide a brief overview of the key projects "
            "and technologies you've worked with."
        )

    def get_softskill_question(self, index: int = 0) -> str:
        """Part 3: Soft skills and behavioral questions."""
        questions = [
            (
                "In your projects, could you describe a challenging situation where you had a tight deadline "
                "or conflicting requirements with your team? How did you prioritize tasks and communicate under pressure?"
            ),
            (
                "Tell me about a time you had a technical disagreement with a teammate or senior engineer "
                "about an architecture or design choice. How did you handle the discussion and reach a constructive consensus?"
            ),
            (
                "How do you approach explaining complex technical concepts or architecture tradeoffs "
                "to non-technical stakeholders, clients, or product managers?"
            ),
            (
                "Looking across your overall experience, what do you consider your greatest technical strength, "
                "and how do you combine that with teamwork, adaptability, and leadership to deliver quality software?"
            )
        ]
        return questions[index % len(questions)]

    def extract_key_skills(self, resume_text: str) -> List[str]:
        """Extracts prominent technical keywords from resume text."""
        common_tech = [
            "TensorFlow", "PyTorch", "Keras", "OpenCV", "Machine Learning", "Deep Learning",
            "Computer Vision", "NLP", "React", "Next.js", "Vue", "Angular", "TypeScript",
            "JavaScript", "Python", "FastAPI", "Django", "Flask", "Node.js", "Express",
            "Docker", "Kubernetes", "AWS", "Azure", "GCP", "PostgreSQL", "MySQL",
            "MongoDB", "Redis", "Kafka", "GraphQL", "REST", "Git", "CI/CD"
        ]
        found = []
        lower_resume = (resume_text or "").lower()
        for tech in common_tech:
            if tech.lower() in lower_resume:
                found.append(tech)
        return found

    def get_fast_technical_question(self, resume_text: str, job_role: str, difficulty: str = "Medium", index: int = 0) -> str:
        """Part 2: Fast resume-grounded technical question."""
        skills = self.extract_key_skills(resume_text)
        exemplars = self.find_question_exemplars(job_role, limit=5)
        
        if skills:
            primary_skill = skills[index % len(skills)]
            secondary_skill = skills[(index + 1) % len(skills)] if len(skills) > 1 else "production deployment"
            
            # Specialized templates based on resume skills
            templates = [
                f"In your work with {primary_skill}, could you walk me through the architecture of a major project where you applied it, and explain how you handled performance optimization and scalability?",
                f"When integrating {primary_skill} alongside {secondary_skill}, what were the most significant technical hurdles or tradeoffs you encountered, and how did you resolve them?",
                f"How did you approach error handling, logging, and automated testing in your {primary_skill} codebase to ensure reliability in production?"
            ]
            return templates[index % len(templates)]
            
        if exemplars and len(exemplars) > index:
            target = exemplars[index].get("target", {})
            if target.get("question"):
                return target.get("question")
                
        return f"Could you elaborate on the most technically challenging project on your resume, detailing your architectural choices and how you measured success?"


# Global singleton
dataset_service = InterviewDatasetService()
