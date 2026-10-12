import re
import math
from typing import Dict, Any, List, Tuple


class ObjectiveScoringService:
    """
    Evaluates candidate interview answers using transparent, deterministic,
    multi-dimensional scoring metrics:
      1. Answer Relevance (25%)
      2. Technical Depth & Domain Entities (35%)
      3. Completeness & Structural Reasoning (20%)
      4. Communication Clarity & Articulation (15%)
      5. Proctoring & Integrity Factor (5%)
    """

    # Domain keywords by role
    TECHNICAL_LEXICON = {
        "full stack": [
            "react", "vue", "angular", "next.js", "typescript", "javascript", "node.js",
            "express", "fastapi", "django", "flask", "postgresql", "mysql", "mongodb",
            "redis", "rest", "graphql", "docker", "kubernetes", "ci/cd", "git", "jwt",
            "state management", "redux", "tailwind", "css", "html", "orm", "prisma",
            "sqlalchemy", "microservices", "caching", "websocket", "aws", "azure"
        ],
        "frontend": [
            "react", "vue", "angular", "next.js", "typescript", "javascript", "css", "html",
            "tailwind", "sass", "redux", "zustand", "context api", "virtual dom", "ssr",
            "ssg", "csr", "webpack", "vite", "performance", "lighthouse", "accessibility",
            "a11y", "responsive", "web vitals", "hydration", "bundle size", "tree shaking"
        ],
        "backend": [
            "python", "fastapi", "django", "flask", "node.js", "go", "java", "spring",
            "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq", "rest",
            "graphql", "grpc", "orm", "sql", "acid", "indexing", "sharding", "replication",
            "microservices", "docker", "kubernetes", "concurrency", "asyncio", "threading",
            "jwt", "oauth", "rate limiting", "load balancing", "caching", "throughput", "latency"
        ],
        "devops": [
            "docker", "kubernetes", "k8s", "terraform", "ansible", "helm", "ci/cd",
            "jenkins", "github actions", "gitlab", "aws", "azure", "gcp", "prometheus",
            "grafana", "elk", "nginx", "linux", "bash", "networking", "vpc", "security",
            "iam", "sre", "slo", "sla", "uptime", "zero downtime", "blue green", "canary"
        ],
        "ml": [
            "python", "pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas",
            "machine learning", "deep learning", "neural network", "transformer", "bert",
            "llm", "rag", "fine-tuning", "lora", "qlora", "cnn", "rnn", "computer vision",
            "nlp", "data preprocessing", "feature engineering", "cross validation",
            "hyperparameter", "accuracy", "precision", "recall", "f1 score", "auc", "roc",
            "overfitting", "regularization", "onnx", "quantization", "embedding", "vector db"
        ],
        "data analyst": [
            "sql", "python", "r", "pandas", "numpy", "tableau", "power bi", "excel",
            "data visualization", "eda", "dashboard", "kpi", "metrics", "etl", "data warehouse",
            "bigquery", "snowflake", "statistical analysis", "hypothesis testing", "ab testing",
            "regression", "correlation", "data cleaning", "reporting", "funnel analysis"
        ]
    }

    # Universal engineering concepts
    UNIVERSAL_ENGINEERING_TERMS = [
        "architecture", "scalability", "performance", "optimization", "latency",
        "throughput", "bottleneck", "concurrency", "asynchronous", "tradeoff",
        "security", "authentication", "authorization", "monitoring", "logging",
        "unit test", "integration test", "e2e", "refactor", "production", "deployment"
    ]

    # Non-answers / evasive responses
    NON_ANSWER_PATTERNS = [
        r"^(i\s+)?(don'?t|do\s+not)\s+know\b",
        r"^(no\s+idea|not\s+sure|i'?m\s+not\s+sure)\b",
        r"^(skip|pass|nothing|idk|n/?a|none)\b",
        r"^(yes|no|yep|nope|sure|ok|okay)\.?$",
        r"^(i\s+have\s+no\s+experience)\b"
    ]

    # STAR structure indicators
    STAR_INDICATORS = {
        "situation": ["in my project", "when i was", "at my previous", "we had a situation", "the context was", "we were building"],
        "task": ["the goal was", "the requirement was", "the challenge was", "i needed to", "the task was", "we had to"],
        "action": ["i implemented", "i designed", "i created", "i integrated", "we decided to", "i optimized", "i refactored", "my approach was"],
        "result": ["which resulted in", "as a result", "this improved", "reduced latency", "increased efficiency", "successfully delivered", "we achieved"]
    }

    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
        "can", "can't", "cannot", "could", "did", "do", "does", "doing", "don't", "down", "during", "each",
        "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
        "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "let's", "me",
        "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some",
        "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these",
        "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were",
        "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your", "yours"
    }

    @classmethod
    def evaluate(
        cls,
        question: str,
        answer: str,
        job_role: str = "",
        resume_text: str = "",
        difficulty: str = "Medium",
        eye_contact_percent: float = None,
        violations: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates honest, objective scores and qualitative feedback based on
        transparent metrics.
        """
        clean_ans = answer.strip()
        lower_ans = clean_ans.lower()
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", clean_ans)
        word_count = len(words)

        # 0. Check for Non-Answers or Evasions
        for pat in cls.NON_ANSWER_PATTERNS:
            if re.search(pat, lower_ans):
                return cls._build_evasion_result(question, answer, job_role)

        if word_count < 4:
            return cls._build_too_short_result(question, answer, word_count)

        # 1. Relevance Score (0-100)
        relevance_score = cls._compute_relevance(question, clean_ans, lower_ans)

        # 2. Technical Depth Score (0-100)
        tech_score, detected_tech = cls._compute_technical_depth(clean_ans, job_role, resume_text, difficulty)

        # 3. Completeness & STAR Reasoning (0-100)
        completeness_score, star_found = cls._compute_completeness(question, clean_ans, lower_ans, word_count)

        # 4. Clarity & Communication (0-100)
        clarity_score = cls._compute_clarity(clean_ans, lower_ans, word_count)

        # 5. Difficulty Weight Multiplier
        # Easy: forgiving baseline; Hard: expects higher technical precision
        diff_factor = 1.05 if difficulty.lower() == "easy" else (0.95 if difficulty.lower() == "hard" else 1.0)
        
        # 6. Weighted Composite Score
        raw_score = (
            (relevance_score * 0.25) +
            (tech_score * 0.35) +
            (completeness_score * 0.20) +
            (clarity_score * 0.20)
        ) * diff_factor

        # Proctoring adjustments (violations penalty)
        if violations > 0:
            raw_score -= min(15, violations * 4)

        # Eye contact adjustment
        if eye_contact_percent is not None:
            if eye_contact_percent >= 70:
                raw_score += 2
            elif eye_contact_percent < 30:
                raw_score -= 3

        overall_score = max(5, min(98, round(raw_score)))
        relevance_score = max(5, min(99, round(relevance_score)))
        tech_score = max(5, min(99, round(tech_score)))
        clarity_score = max(5, min(99, round(clarity_score)))
        completeness_score = max(5, min(99, round(completeness_score)))

        # 7. Formulate honest qualitative strengths and improvements
        strengths, improvements = cls._generate_qualitative_feedback(
            relevance_score, tech_score, completeness_score, clarity_score,
            detected_tech, star_found, word_count
        )

        # 8. Follow-up Needed Flag
        follow_up_needed = (
            word_count < 18 or
            tech_score < 55 or
            completeness_score < 50 or
            overall_score < 65
        )

        eval_summary = cls._generate_narrative(
            overall_score, relevance_score, tech_score, detected_tech, word_count
        )

        return {
            "score": overall_score,
            "relevance": relevance_score,
            "technical_depth": tech_score,
            "clarity": clarity_score,
            "completeness": completeness_score,
            "strengths": strengths,
            "improvements": improvements,
            "evaluation": eval_summary,
            "follow_up_needed": follow_up_needed,
            "metrics_breakdown": {
                "word_count": word_count,
                "detected_skills": detected_tech[:6],
                "star_signals": star_found
            }
        }

    @classmethod
    def _compute_relevance(cls, question: str, clean_ans: str, lower_ans: str) -> float:
        """Measures whether the candidate's answer directly answers the question."""
        q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", question) if w.lower() not in cls.STOP_WORDS]
        if not q_words:
            return 75.0

        ans_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", lower_ans))
        matched = [w for w in q_words if w in ans_words]
        overlap_ratio = len(matched) / len(set(q_words)) if q_words else 0.5

        # Honest relevance curve based on semantic overlap
        if overlap_ratio == 0:
            base = 10.0 if len(ans_words) > 5 else 5.0
        else:
            base = 20.0 + (overlap_ratio * 70.0)

        if len(ans_words) > 15 and overlap_ratio > 0.2:
            base += 5.0
        return min(95.0, base)

    @classmethod
    def _compute_technical_depth(
        cls, clean_ans: str, job_role: str, resume_text: str, difficulty: str
    ) -> Tuple[float, List[str]]:
        """Identifies concrete technical stack terms and architectural depth."""
        lower_ans = clean_ans.lower()
        role_key = "full stack"
        for k in cls.TECHNICAL_LEXICON.keys():
            if k in (job_role or "").lower():
                role_key = k
                break

        role_keywords = cls.TECHNICAL_LEXICON.get(role_key, cls.TECHNICAL_LEXICON["full stack"])
        search_terms = set(role_keywords + cls.UNIVERSAL_ENGINEERING_TERMS)

        detected = []
        for term in search_terms:
            if re.search(r"\b" + re.escape(term) + r"\b", lower_ans):
                detected.append(term)

        count = len(detected)

        # Honest depth scoring curve based on concrete mechanism mentions
        if count == 0:
            tech_score = 15.0  # purely generic fluff without domain substance
        elif count == 1:
            tech_score = 45.0
        elif count == 2:
            tech_score = 65.0
        elif count == 3:
            tech_score = 78.0
        elif count == 4:
            tech_score = 86.0
        else:
            tech_score = min(98.0, 88.0 + (count - 4) * 2.5)

        # Check for architectural tradeoff terminology
        tradeoff_signals = ["tradeoff", "latency", "bottleneck", "cache", "async", "scale", "concurrency", "acid"]
        if any(ts in lower_ans for ts in tradeoff_signals):
            tech_score = min(98.0, tech_score + 6.0)

        return tech_score, detected

    @classmethod
    def _compute_completeness(cls, question: str, clean_ans: str, lower_ans: str, word_count: int) -> Tuple[float, List[str]]:
        """Evaluates whether the candidate provided structured reasoning."""
        star_found = []
        for stage, phrases in cls.STAR_INDICATORS.items():
            if any(p in lower_ans for p in phrases):
                star_found.append(stage)

        # Word count contribution
        if word_count < 10:
            len_score = 25.0
        elif word_count < 25:
            len_score = 55.0
        elif word_count < 60:
            len_score = 75.0
        elif word_count < 150:
            len_score = 88.0
        else:
            len_score = 92.0

        # Structural reasoning bonus
        star_bonus = len(star_found) * 5.0
        completeness = min(96.0, len_score + star_bonus)

        return completeness, star_found

    @classmethod
    def _compute_clarity(cls, clean_ans: str, lower_ans: str, word_count: int) -> float:
        """Measures coherence, grammatical transitions, and absence of filler words."""
        # Detect excessive filler words
        filler_words = ["um", "uh", "like", "you know", "kind of", "sort of", "stuff", "whatever", "basically"]
        filler_count = sum(len(re.findall(r"\b" + re.escape(f) + r"\b", lower_ans)) for f in filler_words)
        filler_ratio = filler_count / max(1, word_count)

        # Transitional words improve clarity
        transitions = ["first", "secondly", "because", "therefore", "for example", "in addition", "specifically", "furthermore"]
        trans_count = sum(1 for t in transitions if t in lower_ans)

        base_clarity = 75.0
        base_clarity += min(15.0, trans_count * 4.0)

        if filler_ratio > 0.08:
            base_clarity -= 18.0
        elif filler_ratio > 0.04:
            base_clarity -= 8.0

        if word_count < 8:
            base_clarity -= 15.0

        return max(20.0, min(95.0, base_clarity))

    @classmethod
    def _generate_qualitative_feedback(
        cls, relevance: float, tech: float, comp: float, clarity: float,
        detected_tech: List[str], star_found: List[str], word_count: int
    ) -> Tuple[List[str], List[str]]:
        strengths = []
        improvements = []

        if detected_tech:
            strengths.append(f"Mentioned concrete technologies & concepts: {', '.join(detected_tech[:4])}")
        elif tech >= 60:
            strengths.append("Addressed the technical framework of the question directly")

        if relevance >= 75:
            strengths.append("Directly aligned response with the core topic asked")

        if star_found:
            strengths.append(f"Used structured problem-solving approach ({', '.join(star_found).title()} highlighted)")

        if clarity >= 75 and word_count >= 20:
            strengths.append("Articulate and structured delivery")

        if not strengths:
            strengths.append("Attempted to respond to the prompt")

        # Areas for improvement
        if not detected_tech:
            improvements.append("Incorporate specific technical tools, frameworks, and architecture decisions rather than generic summaries")

        if word_count < 25:
            improvements.append("Expand on the implementation: detail the problem, tools used, and the measurable end result")

        if "tradeoff" not in " ".join(detected_tech) and tech < 75:
            improvements.append("Highlight production tradeoffs, performance bottlenecks, or edge cases encountered")

        if clarity < 65:
            improvements.append("Reduce filler language and organize your answer into clear, logical steps")

        if not improvements:
            improvements.append("Could further highlight automated testing, CI/CD, or monitoring metrics in production")

        return strengths[:3], improvements[:3]

    @classmethod
    def _generate_narrative(
        cls, overall: int, relevance: float, tech: float, detected_tech: List[str], word_count: int
    ) -> str:
        if overall >= 85:
            return (
                f"Excellent answer ({overall}%). Demonstrated high technical depth with specific concepts "
                f"({', '.join(detected_tech[:3]) if detected_tech else 'well-articulated concepts'}) and clear engineering reasoning."
            )
        elif overall >= 70:
            return (
                f"Good solid answer ({overall}%). Covers the fundamentals effectively. "
                "Adding deeper architectural metrics and performance tradeoffs would elevate this to senior level."
            )
        elif overall >= 50:
            return (
                f"Moderate answer ({overall}%). The response addresses the question at a surface level, "
                "but lacks specific technical tool names, architecture choices, and measurable results."
            )
        else:
            return (
                f"Developing answer ({overall}%). The response was brief ({word_count} words) or evasive. "
                "Please elaborate with real-world examples, specific tech stacks, and step-by-step reasoning."
            )

    @classmethod
    def _build_evasion_result(cls, question: str, answer: str, job_role: str) -> Dict[str, Any]:
        return {
            "score": 15,
            "relevance": 20,
            "technical_depth": 10,
            "clarity": 60,
            "completeness": 10,
            "strengths": ["Acknowledged lack of familiarity honestly"],
            "improvements": [
                "Review foundational concepts related to this topic",
                "Try structuring an answer around adjacent technologies or principles you do know"
            ],
            "evaluation": "The candidate indicated they did not know or could not answer this topic. Foundational review recommended.",
            "follow_up_needed": True,
            "metrics_breakdown": {
                "word_count": len(answer.split()),
                "detected_skills": [],
                "star_signals": []
            }
        }

    @classmethod
    def _build_too_short_result(cls, question: str, answer: str, word_count: int) -> Dict[str, Any]:
        return {
            "score": 25,
            "relevance": 35,
            "technical_depth": 15,
            "clarity": 50,
            "completeness": 15,
            "strengths": ["Briefly answered"],
            "improvements": [
                "Provide a complete, multi-sentence technical response",
                "Name specific tools, architectural patterns, and outcomes"
            ],
            "evaluation": f"Answer was extremely brief ({word_count} words). Comprehensive technical depth was missing.",
            "follow_up_needed": True,
            "metrics_breakdown": {
                "word_count": word_count,
                "detected_skills": [],
                "star_signals": []
            }
        }


# Global singleton
scoring_service = ObjectiveScoringService()
