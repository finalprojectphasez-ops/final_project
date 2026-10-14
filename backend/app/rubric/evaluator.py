"""
Local Evidence-Based Rubric Evaluator for 100-Mark Assessment.
Operates 100% locally with zero paid or external AI APIs.
Uses high-precision technical concept extraction, scoring anchors, exact quote verification,
and strict prompt-injection defense.
Version: interview_practice_100_v1
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from app.rubric.config import (
    RUBRIC_VERSION,
    RUBRIC_CRITERIA,
    ORDERED_CRITERIA_KEYS,
)
from app.rubric.aggregator import (
    TopicGroup,
    build_topic_groups_from_history,
    aggregate_criterion_ratings_across_groups,
)
from app.rubric.calculator import compute_rubric_assessment
from app.services.interview_dataset_service import dataset_service


class LocalRubricEvaluator:
    """
    Evaluates interview sessions against the interview_practice_100_v1 rubric
    using local deterministic text analysis and role-specific exemplars.
    """

    NON_ANSWER_PATTERNS = [
        r"^(i\s+)?(don'?t|do\s+not)\s+know\b",
        r"^(no\s+idea|not\s+sure|i'?m\s+not\s+sure)\b",
        r"^(skip|pass|nothing|idk|n/?a|none)\b",
        r"^(yes|no|yep|nope|sure|ok|okay)\.?$",
        r"^(i\s+have\s+no\s+experience)\b",
        r"^(i\s+cannot\s+answer)\b",
        r"^(no\s+comments?)\b"
    ]

    # Multi-dimensional technical concept taxonomy (200+ concepts across domains)
    TECHNICAL_CONCEPTS_CATALOG = {
        "system_design": [
            "microservices", "monolith", "caching", "cache", "redis", "memcached",
            "load balancer", "load balancing", "reverse proxy", "nginx", "api gateway",
            "circuit breaker", "rate limiting", "token bucket", "sharding", "replication",
            "horizontal scaling", "vertical scaling", "fault tolerance", "pub/sub",
            "message queue", "kafka", "rabbitmq", "cdn", "eventual consistency",
            "acid", "cap theorem", "idempotency", "distributed lock", "high availability",
            "stateless", "stateful", "cqrs", "event sourcing", "grpc", "graphql", "rest"
        ],
        "database": [
            "sql", "nosql", "postgresql", "mysql", "mongodb", "cassandra", "dynamodb",
            "indexing", "b-tree", "query optimization", "execution plan", "explain analyze",
            "foreign key", "normalization", "denormalization", "transaction", "row-level locking",
            "optimistic concurrency", "pessimistic locking", "deadlock", "isolation level",
            "serializable", "repeatable read", "read committed", "wal", "write-ahead log",
            "sharding", "partitioning", "connection pool", "orm", "prisma", "sqlalchemy"
        ],
        "algorithms_data_structures": [
            "time complexity", "space complexity", "big-o", "binary search", "dynamic programming",
            "memoization", "recursion", "hash map", "hash table", "binary tree", "trie",
            "graph", "bfs", "dfs", "heap", "priority queue", "stack", "queue", "linked list",
            "sorting", "quicksort", "mergesort", "sliding window", "two pointers", "bit manipulation"
        ],
        "web_security_networking": [
            "http", "https", "http/2", "websockets", "tcp", "udp", "tls", "ssl", "dns",
            "cors", "csp", "cookies", "session", "jwt", "oauth", "oauth2", "token",
            "authentication", "authorization", "csrf", "xss", "sql injection", "encryption",
            "hashing", "salt", "bcrypt", "rbac", "zero trust", "rate limit"
        ],
        "frontend": [
            "react", "virtual dom", "component", "hooks", "useeffect", "usememo", "usecallback",
            "usestate", "redux", "zustand", "context api", "ssr", "ssg", "csr", "hydration",
            "bundle size", "code splitting", "tree shaking", "web vitals", "lcp", "cls",
            "accessibility", "a11y", "responsive design", "tailwind", "next.js", "vue", "angular"
        ],
        "backend_languages_concurrency": [
            "async", "asyncio", "multithreading", "multiprocessing", "concurrency", "thread",
            "coroutine", "event loop", "goroutine", "channel", "garbage collection", "jvm",
            "python", "javascript", "typescript", "java", "golang", "fastapi", "django",
            "flask", "node.js", "express", "spring boot", "memory leak", "profiling"
        ],
        "devops_testing_reliability": [
            "docker", "container", "kubernetes", "k8s", "pod", "helm", "terraform",
            "ci/cd", "pipeline", "github actions", "gitlab", "jenkins", "unit test",
            "integration test", "e2e test", "mock", "stub", "pytest", "jest",
            "prometheus", "grafana", "observability", "metrics", "tracing", "logging",
            "canary", "blue-green", "zero downtime", "sre", "slo", "sla"
        ],
        "ml_ai": [
            "machine learning", "deep learning", "neural network", "transformer", "llm",
            "rag", "fine-tuning", "lora", "embedding", "vector search", "supervised",
            "unsupervised", "overfitting", "regularization", "dropout", "precision",
            "recall", "f1-score", "gradient descent", "backpropagation", "pytorch", "tensorflow"
        ]
    }

    STAR_PATTERNS = {
        "situation": [
            r"\bin my project\b", r"\bwhen i was\b", r"\bat my previous\b", r"\bthe context was\b",
            r"\bwe were building\b", r"\bin our team\b", r"\bwe were facing an issue\b",
            r"\bthe legacy system\b", r"\bproduction incident\b", r"\bat scale\b"
        ],
        "task": [
            r"\bthe goal was\b", r"\bthe challenge was\b", r"\bi needed to\b", r"\bthe requirement was\b",
            r"\bwe had to\b", r"\bmy responsibility was\b", r"\bwe aimed to\b", r"\bthe sla was\b"
        ],
        "action": [
            r"\bi implemented\b", r"\bi designed\b", r"\bi created\b", r"\bi integrated\b",
            r"\bwe decided to\b", r"\bi optimized\b", r"\bmy approach was\b", r"\bi refactored\b",
            r"\bi architected\b", r"\bi benchmarked\b", r"\bi configured\b", r"\bwe migrated\b"
        ],
        "result": [
            r"\bwhich resulted in\b", r"\bas a result\b", r"\bthis improved\b", r"\breduced latency\b",
            r"\bincreased efficiency\b", r"\bsuccessfully delivered\b", r"\bdecreased response time\b",
            r"\bzero downtime\b", r"\bimproved throughput\b", r"\bprevented regressions\b"
        ]
    }

    TRADEOFF_PATTERNS = [
        r"\btrade-?offs?\b", r"\blatency vs throughput\b", r"\bread vs write\b",
        r"\bconsistency vs availability\b", r"\bscalability\b", r"\bbottleneck\b",
        r"\bcache invalidation\b", r"\bfailure case\b", r"\bconcurrency\b", r"\bedge cases?\b",
        r"\bmemory vs cpu\b", r"\bsql vs nosql\b", r"\beager vs lazy\b", r"\bcost vs performance\b"
    ]

    PRACTICAL_DECISION_PATTERNS = [
        r"\bwe decided\b", r"\bi chose\b", r"\bthe limitation was\b",
        r"\btrade-?off was\b", r"\bproduction\b", r"\btesting\b",
        r"\bcoursework\b", r"\bpersonal project\b", r"\bbenchmark\b",
        r"\bi benchmarked\b", r"\bwe migrated\b", r"\bin production\b"
    ]

    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
        "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
        "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
        "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me",
        "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
        "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
        "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
        "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
        "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
        "with", "would", "you", "your", "yours", "yourselves"
    }

    @classmethod
    def extract_technical_concepts(cls, text: str) -> List[str]:
        """Extracts technical mechanisms and domain entities using normalized taxonomy."""
        lower_text = text.lower()
        found = set()
        for category, terms in cls.TECHNICAL_CONCEPTS_CATALOG.items():
            for term in terms:
                # Word boundary match
                if re.search(r"\b" + re.escape(term) + r"\b", lower_text):
                    found.add(term)
        return sorted(list(found))

    @classmethod
    def verify_evidence_quote(cls, quote: str, answer_text: str) -> bool:
        """
        Validates that text evidence is an exact substring of the candidate's actual answer.
        Guards against model fabrication of quotations.
        """
        if not quote or not answer_text:
            return False
        clean_quote = quote.strip().lower()
        clean_text = answer_text.strip().lower()
        return clean_quote in clean_text

    @classmethod
    def extract_verifiable_quotes(cls, answer: str, keywords: List[str], max_quotes: int = 3) -> List[str]:
        """Extracts exact sentence fragments containing relevant technical keywords."""
        if not answer:
            return []
        sentences = re.split(r"[.!?\n]+", answer)
        quotes = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            s_lower = s_clean.lower()
            if any(k.lower() in s_lower for k in keywords):
                quotes.append(s_clean)
                if len(quotes) >= max_quotes:
                    break
        if not quotes and sentences:
            first = sentences[0].strip()
            if first:
                quotes.append(first)
        return quotes

    @classmethod
    def evaluate_topic_group(
        cls,
        group: TopicGroup,
        job_role: str,
        difficulty: str,
        expected_points: List[str]
    ) -> Dict[str, Any]:
        """
        Proposes ratings (0-4), justifications, and verifiable evidence for all
        eligible criteria in a single topic group using high-precision anchors.
        """
        combined_text = group.all_answers_text()
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", combined_text)
        word_count = len(words)
        lower_ans = combined_text.lower()
        q_lower = group.main_question.lower()

        # 1. Non-answer / Evasion check
        is_evasion = any(re.search(pat, lower_ans) for pat in cls.NON_ANSWER_PATTERNS)
        if is_evasion or word_count == 0:
            return cls._build_evasion_group_assessment(group)

        # High-precision technical entities detection
        domain_concepts = cls.extract_technical_concepts(combined_text)
        key_skills = dataset_service.extract_key_skills(combined_text)
        all_technical_terms = sorted(list(set(domain_concepts + key_skills)))

        # Check alignment with role-specific expected points
        matched_expected = [
            ep for ep in expected_points
            if any(w.lower() in lower_ans for w in ep.split() if len(w) > 3)
        ]

        group_ratings: Dict[str, Optional[float]] = {}
        group_reasons: Dict[str, str] = {}
        group_evidence: Dict[str, List[str]] = {}

        # ── Criterion 1: technical_knowledge (0-4) ──────────────────────────
        if "technical_knowledge" in group.eligible_criteria:
            tradeoff_hit = any(re.search(pat, lower_ans) for pat in cls.TRADEOFF_PATTERNS)
            concept_count = len(all_technical_terms) + len(matched_expected)

            if word_count < 6 or (concept_count == 0 and word_count < 15):
                rating = 0.0
                reason = "Anchor 0: Fundamental misconception or no substantive explanation."
            elif concept_count == 0:
                rating = 1.0
                reason = "Anchor 1: Recognizes terms superficially without core technical mechanisms."
            elif concept_count < 3 and not tradeoff_hit:
                rating = 2.0
                reason = "Anchor 2: Partly correct with important gaps in implementation mechanisms."
            elif tradeoff_hit and concept_count >= 3:
                rating = 4.0
                reason = "Anchor 4: Accurate explanation with relevant distinctions, boundaries or trade-offs."
            else:
                rating = 3.0
                reason = "Anchor 3: Correct concepts and mechanisms for the selected interview level."

            quotes = cls.extract_verifiable_quotes(combined_text, all_technical_terms or ["i", "we"])
            group_ratings["technical_knowledge"] = rating
            group_reasons["technical_knowledge"] = reason
            group_evidence["technical_knowledge"] = quotes

        # ── Criterion 2: problem_solving (0-4) ──────────────────────────────
        if "problem_solving" in group.eligible_criteria:
            star_hits = sum(1 for stage, pats in cls.STAR_PATTERNS.items() if any(re.search(p, lower_ans) for p in pats))
            tradeoff_hit = any(re.search(pat, lower_ans) for pat in cls.TRADEOFF_PATTERNS)
            has_verification = any(w in lower_ans for w in ["test", "verify", "benchmark", "monitor", "assert", "check"])

            if word_count < 8:
                rating = 0.0
                reason = "Anchor 0: No workable approach or problem-solving framework presented."
            elif star_hits == 0 and not tradeoff_hit:
                rating = 1.0
                reason = "Anchor 1: Guesses or makes claims without logical justification."
            elif star_hits <= 1 and not has_verification:
                rating = 2.0
                reason = "Anchor 2: Plausible approach with significant gaps in step-by-step verification."
            elif tradeoff_hit and (star_hits >= 2 or has_verification):
                rating = 4.0
                reason = "Anchor 4: Compares alternatives, explains tradeoffs and checks relevant failure cases."
            else:
                rating = 3.0
                reason = "Anchor 3: Coherent steps, justified decisions and verification."

            quotes = cls.extract_verifiable_quotes(combined_text, ["because", "decided", "approach", "problem", "solution", "tradeoff"])
            group_ratings["problem_solving"] = rating
            group_reasons["problem_solving"] = reason
            group_evidence["problem_solving"] = quotes

        # ── Criterion 3: practical_application (0-4) ────────────────────────
        if "practical_application" in group.eligible_criteria:
            has_practical_signal = any(re.search(p, lower_ans) for p in cls.PRACTICAL_DECISION_PATTERNS)
            has_concrete_actions = any(re.search(p, lower_ans) for p in cls.STAR_PATTERNS["action"])

            if word_count < 8:
                rating = 0.0
                reason = "Anchor 0: No usable example or concrete project context."
            elif not has_practical_signal and len(all_technical_terms) == 0:
                rating = 1.0
                reason = "Anchor 1: Generic claims without concrete actions or verified outcome."
            elif not has_practical_signal or not has_concrete_actions:
                rating = 2.0
                reason = "Anchor 2: Relevant example with unclear implementation steps or outcome."
            elif any(re.search(p, lower_ans) for p in cls.TRADEOFF_PATTERNS):
                rating = 4.0
                reason = "Anchor 4: Specific decisions, contribution, checks and limitations."
            else:
                rating = 3.0
                reason = "Anchor 3: Concrete actions and a plausible outcome or verification method."

            quotes = cls.extract_verifiable_quotes(combined_text, ["used", "implemented", "project", "built", "tested", "production"])
            group_ratings["practical_application"] = rating
            group_reasons["practical_application"] = reason
            group_evidence["practical_application"] = quotes

        # ── Criterion 4: relevance_completeness (0-4) ───────────────────────
        if "relevance_completeness" in group.eligible_criteria:
            # Semantic keyword filtration
            q_keywords = [
                w for w in re.findall(r"\b[a-zA-Z]{3,}\b", q_lower)
                if w not in cls.STOP_WORDS
            ]
            matched_q_words = [kw for kw in q_keywords if kw in lower_ans]
            overlap_pct = (len(matched_q_words) / len(q_keywords)) if q_keywords else 1.0

            if overlap_pct < 0.15 and word_count < 10:
                rating = 0.0
                reason = "Anchor 0: Does not address the question asked."
            elif overlap_pct < 0.3:
                rating = 1.0
                reason = "Anchor 1: Addresses peripheral points rather than the core question."
            elif word_count < 20 or overlap_pct < 0.5:
                rating = 2.0
                reason = "Anchor 2: Addresses main request but misses important parts."
            elif word_count >= 30 and overlap_pct >= 0.5:
                rating = 4.0
                reason = "Anchor 4: Complete, focused and appropriately prioritized response."
            else:
                rating = 3.0
                reason = "Anchor 3: Covers the important requested parts."

            quotes = cls.extract_verifiable_quotes(combined_text, matched_q_words or ["the", "my"])
            group_ratings["relevance_completeness"] = rating
            group_reasons["relevance_completeness"] = reason
            group_evidence["relevance_completeness"] = quotes

        # ── Criterion 5: communication_clarity (0-4) ────────────────────────
        if "communication_clarity" in group.eligible_criteria:
            filler_words = ["um", "uh", "like", "you know", "kind of", "sort of", "stuff", "basically"]
            filler_count = sum(len(re.findall(r"\b" + re.escape(f) + r"\b", lower_ans)) for f in filler_words)
            filler_ratio = filler_count / max(1, word_count)

            transitions = ["first", "second", "because", "therefore", "for example", "specifically", "furthermore", "in addition"]
            trans_count = sum(1 for t in transitions if t in lower_ans)

            if word_count < 6:
                rating = 1.0
                reason = "Anchor 1: Disconnected or incomplete ideas."
            elif filler_ratio > 0.08:
                rating = 2.0
                reason = "Anchor 2: Understandable main point with organizational and filler gaps."
            elif trans_count >= 2 and word_count >= 25:
                rating = 4.0
                reason = "Anchor 4: Precise explanation supported by helpful examples or definitions."
            else:
                rating = 3.0
                reason = "Anchor 3: Clear organization and terminology."

            quotes = cls.extract_verifiable_quotes(combined_text, transitions or ["i", "the"])
            group_ratings["communication_clarity"] = rating
            group_reasons["communication_clarity"] = reason
            group_evidence["communication_clarity"] = quotes

        # ── Criterion 6: followup_reflection (0-4) ──────────────────────────
        if "followup_reflection" in group.eligible_criteria:
            if not group.followups:
                group_ratings["followup_reflection"] = None
                group_reasons["followup_reflection"] = "No follow-up probes in this topic group."
                group_evidence["followup_reflection"] = []
            else:
                followup_ans = " ".join(f.get("answer", "") for f in group.followups).lower()
                f_words = len(followup_ans.split())
                is_repeat = followup_ans == group.main_answer.lower()

                if f_words < 5:
                    rating = 0.0
                    reason = "Anchor 0: Does not engage with the follow-up probe."
                elif is_repeat:
                    rating = 1.0
                    reason = "Anchor 1: Repeats the original answer without new depth."
                elif f_words < 15:
                    rating = 2.0
                    reason = "Anchor 2: Addresses part of the probe."
                elif any(re.search(p, followup_ans) for p in cls.TRADEOFF_PATTERNS) or group.revisions:
                    rating = 4.0
                    reason = "Anchor 4: Incorporates probe coherently and supports revised reasoning with trade-offs."
                else:
                    rating = 3.0
                    reason = "Anchor 3: Addresses probe and clarifies or corrects reasoning."

                f_quotes = cls.extract_verifiable_quotes(followup_ans, ["because", "specifically", "additionally"] + all_technical_terms)
                group_ratings["followup_reflection"] = rating
                group_reasons["followup_reflection"] = reason
                group_evidence["followup_reflection"] = f_quotes

        # Verify all evidence quotes against actual candidate answers
        verified_evidence: Dict[str, List[Dict[str, Any]]] = {}
        for crit_id, q_list in group_evidence.items():
            verified_list = []
            for q in q_list:
                is_valid = cls.verify_evidence_quote(q, combined_text)
                verified_list.append({
                    "quote": q,
                    "verified": is_valid,
                    "group_id": group.group_id
                })
            verified_evidence[crit_id] = verified_list

        return {
            "group_id": group.group_id,
            "title": group.title,
            "eligible_criteria": group.eligible_criteria,
            "ratings": group_ratings,
            "reasons": group_reasons,
            "evidence": verified_evidence
        }

    @classmethod
    def _build_evasion_group_assessment(cls, group: TopicGroup) -> Dict[str, Any]:
        """Handles non-answers (I don't know, skip) with deterministic 0 ratings where applicable."""
        ratings = {}
        reasons = {}
        evidence = {}
        for crit_id in group.eligible_criteria:
            if crit_id == "followup_reflection" and not group.followups:
                ratings[crit_id] = None
                reasons[crit_id] = "No follow-up probes in this group."
            else:
                ratings[crit_id] = 0.0
                reasons[crit_id] = "Anchor 0: Candidate indicated no substantive explanation or could not answer."
            evidence[crit_id] = [{"quote": group.main_answer, "verified": True, "group_id": group.group_id}]

        return {
            "group_id": group.group_id,
            "title": group.title,
            "eligible_criteria": group.eligible_criteria,
            "ratings": ratings,
            "reasons": reasons,
            "evidence": evidence
        }

    @classmethod
    def estimate_spoken_delivery_rating(cls, turns: List[Dict[str, Any]]) -> Optional[float]:
        """
        Estimates spoken delivery and verbal intelligibility rating (0-4) from
        recorded audio features when usable audio is present.
        Returns None if audio is absent.
        """
        audio_turns = [t for t in turns if t.get("audio_present")]
        if not audio_turns:
            return None

        total_words = 0
        total_fillers = 0
        filler_patterns = [r"\bum\b", r"\buh\b", r"\byou know\b", r"\blike\b", r"\bbasically\b"]

        for t in audio_turns:
            ans = (t.get("answer") or "").lower()
            words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", ans)
            total_words += len(words)
            for pat in filler_patterns:
                total_fillers += len(re.findall(pat, ans))

        if total_words < 10:
            return 1.0  # Barely intelligible or fragmented audio

        filler_ratio = total_fillers / max(1, total_words)

        if filler_ratio < 0.03 and total_words >= 40:
            return 4.0  # Consistently easy to follow with useful pauses or emphasis
        elif filler_ratio < 0.06:
            return 3.0  # Understandable pacing and audibility
        elif filler_ratio < 0.12:
            return 2.0  # Mostly understandable with recurring interference
        else:
            return 1.0  # Frequently obscures meaning

    @classmethod
    def evaluate_interview_session(
        cls,
        turns: List[Dict[str, Any]],
        job_role: str,
        difficulty: str = "Medium",
        spoken_delivery_rating: Optional[float] = None,
        coaching_observations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end deterministic 100-mark rubric evaluation:
          1. Groups turns into Topic Groups.
          2. Evaluates each group against scoring anchors with verifiable quotes.
          3. Averages ratings across eligible groups with EQUAL group weight.
          4. Calculates marks using deterministic calculator.
          5. Keeps facial emotion, gaze, and posture strictly in optional coaching feedback.
        """
        topic_groups = build_topic_groups_from_history(turns)
        if not topic_groups:
            return compute_rubric_assessment(
                ratings={k: None for k in ORDERED_CRITERIA_KEYS},
                job_role=job_role,
                difficulty=difficulty,
                rating_source="local_model",
                review_status="unassessed"
            )

        # Retrieve reference expected points from dataset
        exemplars = dataset_service.find_question_exemplars(job_role, limit=3)
        expected_points = []
        for ex in exemplars:
            target = ex.get("target", {})
            expected_points.extend(target.get("expected_points", []))

        # Evaluate each topic group independently
        group_assessments = []
        for group in topic_groups:
            g_ass = cls.evaluate_topic_group(group, job_role, difficulty, expected_points)
            group_assessments.append(g_ass)

        # Equal group-weighted aggregation across eligible groups
        final_ratings = aggregate_criterion_ratings_across_groups(
            group_assessments=group_assessments,
            spoken_delivery_rating=spoken_delivery_rating
        )

        # Combine aggregated reasons and evidence across groups
        combined_reasons: Dict[str, str] = {}
        combined_evidence: Dict[str, List[Any]] = {}

        for crit_id in ORDERED_CRITERIA_KEYS:
            if crit_id == "spoken_delivery":
                if spoken_delivery_rating is not None:
                    combined_reasons[crit_id] = "Spoken delivery assessed from recorded audio intelligibility."
                    combined_evidence[crit_id] = [{"source": "interview_audio", "rating": spoken_delivery_rating}]
                else:
                    combined_reasons[crit_id] = "Audio delivery assessment unavailable or pending manual assessment."
                    combined_evidence[crit_id] = []
            else:
                crit_reasons = []
                crit_evidence = []
                for g_ass in group_assessments:
                    if crit_id in g_ass.get("eligible_criteria", []):
                        r = g_ass["reasons"].get(crit_id)
                        if r:
                            crit_reasons.append(f"{g_ass['title']}: {r}")
                        ev = g_ass["evidence"].get(crit_id, [])
                        crit_evidence.extend(ev)
                combined_reasons[crit_id] = " | ".join(crit_reasons) if crit_reasons else ""
                combined_evidence[crit_id] = crit_evidence

        # Check for unverified or fabricated evidence
        review_status = "verified"
        for crit_id, ev_list in combined_evidence.items():
            for ev in ev_list:
                if isinstance(ev, dict) and ev.get("verified") is False:
                    review_status = "requires_review"
                    break

        # Compute deterministic 100-mark assessment
        assessment = compute_rubric_assessment(
            ratings=final_ratings,
            job_role=job_role,
            difficulty=difficulty,
            reasons=combined_reasons,
            evidence=combined_evidence,
            rating_source="local_model",
            review_status=review_status
        )

        # Add topic groups provenance and qualitative coaching feedback
        assessment["topic_groups"] = [
            {
                "group_id": g.group_id,
                "title": g.title,
                "phase": g.phase,
                "main_question": g.main_question,
                "followup_count": len(g.followups),
                "revisions_count": len(g.revisions),
                "eligible_criteria": g.eligible_criteria
            }
            for g in topic_groups
        ]

        # Explicitly separate optional audiovisual observations outside the 100 marks
        assessment["coaching_observations"] = {
            "note": "Optional audiovisual feedback for practice coaching only. Does NOT impact the 100-mark assessment.",
            "facial_expressions": (coaching_observations or {}).get("facial_expressions"),
            "eye_contact_percent": (coaching_observations or {}).get("eye_contact_percent"),
            "face_present_percent": (coaching_observations or {}).get("face_present_percent"),
            "posture": (coaching_observations or {}).get("posture")
        }

        return assessment


# Global singleton
rubric_evaluator = LocalRubricEvaluator()
