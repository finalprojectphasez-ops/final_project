import os
import re
import json
import random
import logging
from pathlib import Path
from openai import AsyncOpenAI
from typing import List, Dict, Optional
from app.models.schemas import InterviewContext
from app.config import settings

logger = logging.getLogger("uvicorn.error")

if settings.GROQ_API_KEY:
    client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
elif settings.OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
else:
    client = None

# Standard curated question tracks by role & difficulty
ROLE_QUESTION_BANKS = {
    "Full Stack Engineer": {
        "Easy": [
            "Could you walk me through the lifecycle of an HTTP request from the browser until data is returned from your backend?",
            "How do you manage client-side vs. server-side state in modern frameworks like React or Next.js?",
            "What strategies do you use for database indexing and optimizing slow queries?",
            "Can you discuss an instance where you had to debug a difficult cross-stack bug?",
            "How do you approach authentication and secure token handling across frontend and backend services?"
        ],
        "Medium": [
            "Given your full stack experience, how would you design a real-time notification system handling 50,000 concurrent active connections?",
            "How do you handle schema migrations in production with zero downtime for relational databases?",
            "What are the trade-offs between Server-Side Rendering (SSR), Static Site Generation (SSG), and Client-Side Rendering (CSR)?",
            "Suppose your backend API response latency suddenly spikes from 50ms to 2000ms under high load. How would you systematically diagnose the bottleneck?",
            "Describe a time you had to balance building a quick feature versus paying down technical debt in your codebase."
        ],
        "Hard": [
            "How would you architect a distributed, event-driven microservices architecture ensuring eventual consistency and idempotent event processing?",
            "Walk me through how you would implement distributed rate limiting across a horizontally scaled cluster of API gateways.",
            "Can you explain database sharding strategies versus read-replicas, and how you resolve distributed deadlocks or race conditions?",
            "If your application experiences memory leaks in a production Node.js or Python backend container, how would you profile and isolate the root cause?",
            "Describe a complex architectural trade-off you championed that had long-term implications for your engineering organization."
        ]
    },
    "Frontend Developer": {
        "Easy": [
            "Can you explain the difference between the browser's Document Object Model (DOM) and the Virtual DOM?",
            "How do you approach responsive web design and cross-browser CSS compatibility?",
            "What is the event loop in JavaScript, and how do microtasks differ from macrotasks?",
            "How do you optimize web performance metrics like Core Web Vitals (LCP, FID/INP, CLS)?",
            "Can you explain how accessibility (a11y) considerations factor into your component development?"
        ],
        "Medium": [
            "How do you diagnose and prevent unnecessary re-renders in complex React applications?",
            "Explain how you would architect a reusable, accessible design system component library across multiple teams.",
            "How do modern bundlers like Turbopack or Vite differ from Webpack in terms of module graph construction and HMR?",
            "What strategies do you use for caching API data on the client side without introducing stale state issues?",
            "Tell me about a challenging UI interaction or animation you built and how you ensured 60fps smoothness."
        ],
        "Hard": [
            "How would you design a client-side offline-first architecture with conflict resolution and background sync via Service Workers?",
            "Explain micro-frontend architecture: what are the concrete trade-offs in bundle size, dependency sharing, and runtime isolation?",
            "How do you audit and remediate client-side memory leaks caused by lingering event listeners, closures, or detached DOM nodes?",
            "If you were tasked with building a web-based collaborative canvas (like Figma) in the browser, what rendering technology and synchronization protocol would you choose?",
            "Describe a critical architectural mistake you made in a frontend application and how you remediated it."
        ]
    },
    "Backend Engineer": {
        "Easy": [
            "Can you explain the differences between RESTful APIs and RPC-based architectures like gRPC?",
            "What are ACID transactions in relational databases, and how do isolation levels impact data integrity?",
            "How do you design a database schema for a relational database versus a NoSQL document store?",
            "What is connection pooling, and why is it necessary for production database backends?",
            "How do you implement secure password storage and hashing in a backend system?"
        ],
        "Medium": [
            "How do you design an asynchronous task processing pipeline using queues like RabbitMQ, Celery, or Kafka?",
            "Suppose two concurrent requests attempt to deduct funds from the same account balance simultaneously. How do you prevent race conditions?",
            "Can you compare Redis caching strategies: Cache-Aside vs. Write-Through vs. Write-Behind?",
            "How do you monitor, log, and trace distributed requests using tools like OpenTelemetry or Prometheus?",
            "Walk me through your approach to database indexing: composite indexes, index selectivity, and query execution plans."
        ],
        "Hard": [
            "How would you design a distributed transactional ledger supporting high throughput with strict consistency guarantees?",
            "Explain the CAP theorem and PACELC theorem in the context of designing a multi-region distributed datastore.",
            "How would you design and implement a distributed locking mechanism using Redis (Redlock) or ZooKeeper/Etcd, and what are its failure modes?",
            "If your database connection pool is exhausted during a traffic spike, what cascading failure mitigations (circuit breaking, bulkhead pattern) would you put in place?",
            "Describe how you would design a webhook delivery system that guarantees at-least-once delivery with exponential backoff and jitter."
        ]
    },
    "DevOps / SRE": {
        "Easy": [
            "Can you explain the core differences between a container (Docker) and a Virtual Machine?",
            "What is Continuous Integration and Continuous Deployment (CI/CD), and how do you structure a pipeline?",
            "How does DNS resolution work from domain query to server IP address?",
            "What are common Linux command-line utilities you use to inspect CPU, memory, and disk I/O bottlenecks?",
            "Can you describe how SSL/TLS certificate handshakes establish encryption?"
        ],
        "Medium": [
            "How do Kubernetes Pods communicate internally via ClusterIP, NodePort, and Ingress controllers?",
            "How do you implement Infrastructure as Code (IaC) using Terraform, and how do you manage state locking in team settings?",
            "What is the difference between Blue-Green deployments and Canary releases, and how do you automate rollbacks?",
            "How do you design automated alerts that minimize alert fatigue while maintaining strong Service Level Objectives (SLOs)?",
            "Walk me through how you would secure secrets in a containerized environment (e.g., HashiCorp Vault vs. cloud KMS)."
        ],
        "Hard": [
            "How would you architect a disaster recovery plan with near-zero RTO (Recovery Time Objective) and RPO (Recovery Point Objective) across multiple cloud regions?",
            "Explain how Linux cgroups and namespaces enforce container resource limits and isolation, and what happens during an OOM kill event.",
            "How do you troubleshoot a Kubernetes cluster experiencing network partition or control plane ETCD quorum loss?",
            "Design a zero-trust network architecture for a high-compliance fintech infrastructure.",
            "Describe a major production outage you triaged, your incident command approach, and the blameless post-mortem actions taken."
        ]
    },
    "ML Engineer": {
        "Easy": [
            "What is the difference between supervised, unsupervised, and reinforcement learning?",
            "How do you detect and mitigate overfitting in machine learning models?",
            "Can you explain precision, recall, F1-score, and ROC-AUC, and when each metric is most appropriate?",
            "What is feature engineering, and how do you handle missing or categorical data?",
            "How do gradient descent and learning rate scheduling work?"
        ],
        "Medium": [
            "How do you build a real-time inference pipeline with sub-50ms latency for a deep learning model?",
            "What is data drift and concept drift, and how do you monitor for model degradation in production?",
            "Explain the architectural mechanisms behind Transformer models, specifically self-attention and multi-head attention.",
            "How do you handle model versioning, feature stores, and experiment tracking using tools like MLflow or Feast?",
            "Walk me through how you would optimize a model for edge deployment using quantization and pruning."
        ],
        "Hard": [
            "How would you architect a distributed training infrastructure for large language models across multi-GPU/multi-node clusters?",
            "Design a real-time recommendation engine processing millions of candidate items with a two-stage retrieval and ranking pipeline.",
            "How do Retrieval-Augmented Generation (RAG) pipelines manage chunking strategies, vector embeddings, and re-ranking for enterprise data?",
            "Describe how you would evaluate and safeguard an LLM application against prompt injection, hallucinations, and data leakage.",
            "What was the most challenging ML model you deployed into production, and how did you validate its real-world business impact?"
        ]
    },
    "Data Analyst": {
        "Easy": [
            "What is the difference between WHERE and HAVING clauses in SQL?",
            "Can you explain SQL window functions (like ROW_NUMBER, RANK, and DENSE_RANK)?",
            "How do you approach exploratory data analysis (EDA) when receiving a messy dataset?",
            "What are the main differences between star schema and snowflake schema in data warehousing?",
            "How do you choose between different visualization types (scatter plot, box plot, bar chart, heat map) to convey insights?"
        ],
        "Medium": [
            "How do you design an executive dashboard in tools like Tableau or PowerBI that drives actionable decision-making?",
            "Explain how you would calculate Customer Lifetime Value (LTV) and Churn Rate using SQL and cohort analysis.",
            "How do you design and evaluate an A/B test: sample size determination, statistical significance, and p-value interpretation?",
            "What is the difference between an OLTP database and an OLAP data warehouse (like Snowflake or BigQuery)?",
            "Walk me through an analysis where your findings directly changed a strategic company decision."
        ],
        "Hard": [
            "How do you handle attribution modeling for multi-touch marketing funnels across disparate touchpoints?",
            "How do you build automated anomaly detection models to alert business teams of sudden metric deviations?",
            "Explain causal inference techniques (such as difference-in-differences or synthetic controls) when randomized A/B testing is infeasible.",
            "How would you design a data governance, semantic layer, and data quality framework for a fast-scaling analytics team?",
            "Describe a project where raw data was conflicting or unreliable, and how you arrived at defensible, high-confidence insights."
        ]
    }
}

class LLMEngine:
    def __init__(self, context: InterviewContext):
        self.context = context
        self.question_index = 0
        
        # Pull from Kaggle dataset if no resume provided
        if not self.context.resume_text.strip():
            self._inject_dataset_resume()
            
        self.extracted_skills = self._extract_skills(self.context.resume_text)
        self.history = [
            {"role": "system", "content": self._build_system_prompt()}
        ]
        
    def _inject_dataset_resume(self):
        try:
            backend_dir = Path(__file__).parent.parent.parent
            json_path = backend_dir / "data" / "resume_dataset" / "cleaned_resumes.json"
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    dataset = json.load(f)
                
                # Try to get resumes for the current role
                role_resumes = dataset.get(self.context.role, [])
                if role_resumes:
                    self.context.resume_text = random.choice(role_resumes)
                else:
                    # Fallback to random if role not found
                    all_resumes = [r for sublist in dataset.values() for r in sublist]
                    if all_resumes:
                        self.context.resume_text = random.choice(all_resumes)
                logger.info(f"[LLMEngine] Injected realistic resume for role: {self.context.role}")
        except Exception as e:
            logger.error(f"[LLMEngine] Failed to load dataset resume: {e}")
        
    def _extract_skills(self, text: str) -> List[str]:
        """Detect technical keywords mentioned in the uploaded resume."""
        keywords = [
            "Python", "JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Vue", "Angular",
            "FastAPI", "Django", "Flask", "Go", "Golang", "Java", "Spring Boot", "C++", "C#", ".NET",
            "Docker", "Kubernetes", "AWS", "Azure", "GCP", "PostgreSQL", "MySQL", "MongoDB", "Redis",
            "Kafka", "GraphQL", "REST", "CI/CD", "Terraform", "Git", "PyTorch", "TensorFlow",
            "Pandas", "SQL", "TailwindCSS", "Linux", "Microservices", "System Design"
        ]
        found = []
        lower_text = text.lower()
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, lower_text):
                found.append(kw)
        return found[:6]

    def _build_system_prompt(self) -> str:
        skills_str = ", ".join(self.extracted_skills) if self.extracted_skills else "General technical foundations"
        return f"""You are a professional, rigorous hiring manager conducting an interview.
Role: {self.context.role}
Difficulty: {self.context.difficulty}
Detected Skills from Resume: {skills_str}
Resume Excerpt: {self.context.resume_text[:1500]}

Rules:
1. Ask exactly ONE targeted question at a time.
2. If candidate answers well, acknowledge it briefly and dig deeper into edge cases, architecture, or trade-offs.
3. Keep questions direct, highly realistic, and professional."""

    async def get_next_question(self, user_answer: Optional[str] = None) -> str:
        if user_answer:
            self.history.append({"role": "user", "content": user_answer})

        # 1. Try LLM if API key is provided
        if client:
            try:
                model_name = "llama-3.1-70b-versatile" if settings.GROQ_API_KEY else "gpt-4o"
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=self.history,
                    temperature=0.7,
                    max_tokens=150,
                    timeout=10.0
                )
                reply = response.choices[0].message.content.strip()
                self.history.append({"role": "assistant", "content": reply})
                self.question_index += 1
                return reply
            except Exception as e:
                logger.warning(f"[LLMEngine] LLM API call failed ({e}). Using intelligent dynamic fallback question generator.")

        # 2. Fallback Question Generator (100% reliable, zero external dependencies)
        return self._generate_fallback_question(user_answer)

    def _generate_fallback_question(self, user_answer: Optional[str] = None) -> str:
        role = self.context.role if self.context.role in ROLE_QUESTION_BANKS else "Full Stack Engineer"
        diff = self.context.difficulty if self.context.difficulty in ["Easy", "Medium", "Hard"] else "Medium"
        bank = ROLE_QUESTION_BANKS.get(role, ROLE_QUESTION_BANKS["Full Stack Engineer"]).get(diff, [])

        # First question: personalized with resume if skills detected
        if self.question_index == 0:
            self.question_index += 1
            if self.extracted_skills:
                primary_skill = self.extracted_skills[0]
                secondary_skills = ", ".join(self.extracted_skills[1:3])
                q = (
                    f"Welcome! I reviewed your resume and noticed your experience with {primary_skill}"
                    + (f" alongside {secondary_skills}." if secondary_skills else ".")
                    + f" Could you walk me through an impactful project where you architected solutions using {primary_skill}, and highlight the most challenging technical hurdle you resolved?"
                )
            else:
                q = (
                    f"Welcome to your {self.context.role} interview. "
                    + bank[0] if bank else f"Could you introduce yourself and walk me through your technical background in {self.context.role}?"
                )
            self.history.append({"role": "assistant", "content": q})
            return q

        # Subsequent questions: follow up based on user answer & question bank
        idx = self.question_index
        self.question_index += 1

        prefix = ""
        if user_answer and len(user_answer.split()) > 6:
            # Pick a relevant transition based on answer length & context
            transitions = [
                "That provides good context on your approach.",
                "Thank you for that explanation.",
                "Understood, that highlights your thought process well.",
                "Good technical breakdown."
            ]
            prefix = transitions[(idx - 1) % len(transitions)] + " "

        if idx < len(bank):
            next_q = prefix + bank[idx]
        elif self.extracted_skills and (idx - len(bank)) < len(self.extracted_skills):
            skill = self.extracted_skills[(idx - len(bank)) % len(self.extracted_skills)]
            next_q = f"{prefix}Moving to another area from your resume: how do you manage testing, CI/CD automation, and deployment safety when working with {skill}?"
        else:
            next_q = f"{prefix}To conclude our session: looking back at the architectural decisions we discussed, what would you do differently if you had to scale the system by 10x tomorrow?"

        self.history.append({"role": "assistant", "content": next_q})
        return next_q

    async def generate_evaluation(self, full_transcript: List[Dict]) -> dict:
        """
        Evaluate the completed interview session.

        History structure (built by get_next_question / _generate_fallback_question):
          history[0]           → {role: "system",    content: system_prompt}
          history[1]           → {role: "assistant",  content: first_question}
          history[2]           → {role: "user",       content: first_answer}
          history[3]           → {role: "assistant",  content: second_question}
          history[4]           → {role: "user",       content: second_answer}
          ...

        Returns a dict that maps 1-to-1 with EvaluationResponse / interview_sessions columns.
        """
        # ── Extract Q&A pairs from history ──────────────────────────────────
        qa_pairs: List[Dict] = []
        msgs = self.history  # use the instance history (always up-to-date)
        i = 1  # skip system prompt at index 0
        while i < len(msgs) - 1:
            if msgs[i]["role"] == "assistant" and msgs[i + 1]["role"] == "user":
                qa_pairs.append({
                    "question": msgs[i]["content"].strip(),
                    "answer":   msgs[i + 1]["content"].strip(),
                })
                i += 2
            else:
                i += 1

        if not qa_pairs:
            # Session ended before any answer was submitted — return minimal result
            return self._minimal_evaluation()

        # ── 1. Try LLM structured evaluation ─────────────────────────────
        if client:
            try:
                result = await self._openai_evaluate(qa_pairs)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"[LLMEngine] LLM evaluation failed ({e}). Using rule-based fallback.")

        # ── 2. Rule-based evaluation (no external dependencies) ──────────────
        return self._rule_based_evaluate(qa_pairs)

    # ── OpenAI evaluation ────────────────────────────────────────────────────

    async def _openai_evaluate(self, qa_pairs: List[Dict]) -> Optional[dict]:
        """Ask GPT-4o to evaluate the full transcript and return structured JSON."""
        transcript_text = "\n\n".join(
            f"Q{i+1}: {p['question']}\nA{i+1}: {p['answer']}"
            for i, p in enumerate(qa_pairs)
        )
        system_msg = (
            f"You are a senior hiring manager evaluating a {self.context.role} "
            f"interview at {self.context.difficulty} difficulty. "
            "Analyse the transcript and return ONLY valid JSON with exactly these keys:\n"
            "overall_score (0-100 int), technical_score (0-100 int), "
            "communication_score (0-100 int), answer_relevance (0-100 int), "
            "strengths (list of 3 strings), weaknesses (list of 3 strings), "
            "improvement_suggestions (list of 3 strings), practice_areas (list of 3 strings), "
            "general_feedback (2-3 sentence string), "
            "question_feedback (list of objects each with: question, answer, score 0-100, feedback string)."
        )
        model_name = "llama-3.1-70b-versatile" if settings.GROQ_API_KEY else "gpt-4o"
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system",  "content": system_msg},
                {"role": "user",    "content": f"Interview transcript:\n\n{transcript_text}"},
            ],
            temperature=0.3,
            max_tokens=1200,
            timeout=20.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        # Normalise question_feedback to include question + answer text
        qf = []
        for idx, item in enumerate(data.get("question_feedback", [])):
            pair = qa_pairs[idx] if idx < len(qa_pairs) else {}
            qf.append({
                "question": item.get("question", pair.get("question", "")),
                "answer":   item.get("answer",   pair.get("answer",   "")),
                "score":    int(item.get("score", 70)),
                "feedback": item.get("feedback", ""),
            })
        # Fill missing entries if GPT returned fewer items than pairs
        for idx in range(len(qf), len(qa_pairs)):
            qf.append({
                "question": qa_pairs[idx]["question"],
                "answer":   qa_pairs[idx]["answer"],
                "score":    70,
                "feedback": "Answer assessed.",
            })
        data["question_feedback"] = qf

        # Clamp scores
        for key in ("overall_score", "technical_score", "communication_score", "answer_relevance"):
            data[key] = max(0, min(100, int(data.get(key, 70))))

        return data

    # ── Rule-based evaluation ────────────────────────────────────────────────

    # Technical terms that signal strong, specific answers
    TECH_TERMS = {
        "algorithm", "complexity", "o(n", "o(log", "cache", "index", "async", "await",
        "promise", "thread", "mutex", "race condition", "deadlock", "distributed",
        "microservice", "api", "rest", "graphql", "http", "tcp", "dns", "cdn",
        "database", "sql", "nosql", "transaction", "acid", "cap theorem",
        "kubernetes", "docker", "ci/cd", "pipeline", "deployment", "load balanc",
        "horizontal", "vertical", "shard", "replica", "partition", "throughput",
        "latency", "bottleneck", "profil", "benchmark", "test", "tdd", "bdd",
        "design pattern", "solid", "dry", "abstraction", "encapsulat",
        "polymorphism", "inheritance", "interface", "dependency injection",
        "memory", "heap", "stack", "garbage collect", "pointer", "buffer",
        "token", "oauth", "jwt", "encrypt", "hash", "salt", "cors", "csrf",
        "webpack", "vite", "bundle", "tree shak", "lazy load", "virtual dom",
        "react", "vue", "angular", "next", "server side", "client side", "ssr",
        "python", "javascript", "typescript", "golang", "java", "rust", "c++",
    }

    # Sentence-structure markers that indicate clear communication
    COMM_MARKERS = {
        "because", "therefore", "however", "although", "which means",
        "for example", "such as", "in other words", "specifically",
        "first", "second", "third", "finally", "additionally",
        "the reason", "the benefit", "the trade-off", "in my experience",
        "i would", "i have", "we used", "i implemented", "i built",
    }

    def _score_answer(self, question: str, answer: str) -> Dict:
        """
        Score a single Q&A pair on three axes and produce feedback.
        Returns {score, technical_contribution, communication_contribution,
                 relevance_contribution, feedback}.
        """
        words = answer.lower().split()
        word_count = len(words)
        answer_lower = answer.lower()
        question_lower = question.lower()

        # ── Completeness (0-40 pts): based on answer length ──
        if word_count == 0:
            completeness = 0
        elif word_count < 20:
            completeness = 10
        elif word_count < 50:
            completeness = 20
        elif word_count < 100:
            completeness = 30
        else:
            completeness = 40

        # ── Technical depth (0-35 pts): tech term density ──
        tech_hits = sum(1 for t in self.TECH_TERMS if t in answer_lower)
        tech_score_raw = min(35, tech_hits * 7)

        # ── Communication (0-25 pts): structure markers ──
        comm_hits = sum(1 for m in self.COMM_MARKERS if m in answer_lower)
        comm_score_raw = min(25, comm_hits * 6)

        # ── Relevance bonus: keyword overlap with question ──
        q_words = set(re.sub(r'[^\w\s]', '', question_lower).split()) - {
            "the","a","an","is","are","what","how","why","when","where","you","your",
            "can","could","would","should","do","does","did","have","has","had","will",
            "and","or","but","if","in","on","at","to","of","for","with","that","this",
        }
        a_words = set(re.sub(r'[^\w\s]', '', answer_lower).split())
        overlap = len(q_words & a_words)
        relevance_bonus = min(10, overlap * 2)

        raw = completeness + tech_score_raw + comm_score_raw + relevance_bonus
        score = max(10, min(100, raw))

        # ── Verbal feedback ──
        if score >= 80:
            feedback = (
                "Strong, detailed answer with good technical depth. "
                "You demonstrated clear reasoning and relevant specifics."
            )
        elif score >= 60:
            feedback = (
                "Solid response covering the core points. "
                "Adding more concrete examples or trade-off analysis would strengthen it further."
            )
        elif score >= 40:
            feedback = (
                "Partial answer — you touched on the right area but lacked depth. "
                "Try to explain the 'why' and include specific technical details."
            )
        else:
            feedback = (
                "The answer was too brief or did not address the question directly. "
                "Practice structuring responses: state your approach, give an example, explain trade-offs."
            )

        return {
            "score":                    score,
            "technical_contribution":   tech_score_raw,
            "communication_contribution": comm_score_raw,
            "relevance_contribution":   relevance_bonus,
            "feedback":                 feedback,
        }

    def _rule_based_evaluate(self, qa_pairs: List[Dict]) -> dict:
        """
        Deterministic evaluation using the scoring rubric above.
        Produces the full EvaluationResponse-compatible dict.
        """
        scored = []
        for pair in qa_pairs:
            result = self._score_answer(pair["question"], pair["answer"])
            scored.append({**pair, **result})

        scores      = [s["score"] for s in scored]
        tech_vals   = [s["technical_contribution"] for s in scored]
        comm_vals   = [s["communication_contribution"] for s in scored]
        rel_vals    = [s["relevance_contribution"] for s in scored]

        def avg(lst): return int(round(sum(lst) / len(lst))) if lst else 0

        overall_score       = avg(scores)
        # Scale sub-scores to 0-100
        technical_score     = min(100, int(avg(tech_vals) * 100 / 35))
        communication_score = min(100, int(avg(comm_vals) * 100 / 25))
        answer_relevance    = min(100, int(avg(rel_vals)  * 100 / 10))

        # ── Strengths ──
        strengths = []
        if technical_score >= 60:
            strengths.append(f"Demonstrated solid technical knowledge relevant to {self.context.role}.")
        if communication_score >= 60:
            strengths.append("Communicated answers clearly with good use of structure and examples.")
        if answer_relevance >= 60:
            strengths.append("Responses stayed focused and directly addressed the questions asked.")
        if overall_score >= 75:
            strengths.append("Maintained consistent quality across multiple questions.")
        if len(strengths) < 2:
            strengths.append("Showed willingness to engage with complex technical topics.")

        # ── Weaknesses ──
        weaknesses = []
        if technical_score < 60:
            weaknesses.append("Answers lacked sufficient technical depth and specificity.")
        if communication_score < 60:
            weaknesses.append("Could improve clarity by using structured communication (e.g., 'First... Then... Finally...').")
        if answer_relevance < 60:
            weaknesses.append("Some answers drifted from the core question — focus on directly addressing what is asked.")
        if any(s["score"] < 40 for s in scored):
            weaknesses.append("One or more questions received minimal responses — aim for at least 50+ word answers.")
        if len(weaknesses) < 2:
            weaknesses.append("Practice elaborating on answers with concrete real-world examples.")

        # ── Improvement suggestions ──
        improvement_suggestions = [
            "Use the STAR method (Situation, Task, Action, Result) for behavioural questions.",
            f"Study advanced topics specific to {self.context.role} at {self.context.difficulty} difficulty.",
            "Record yourself answering common questions to improve verbal clarity and pacing.",
        ]

        # ── Practice areas ──
        practice_areas = [self.context.role + " fundamentals", "System design", "Communication skills"]
        if self.context.difficulty == "Hard":
            practice_areas.append("Advanced distributed systems")
        elif self.context.difficulty == "Medium":
            practice_areas.append("Intermediate architecture patterns")

        # ── General feedback ──
        if overall_score >= 80:
            verdict = "Strong performance"
            tone    = "You are well-prepared for industry interviews at this level."
        elif overall_score >= 65:
            verdict = "Solid showing"
            tone    = "With focused practice on depth and structure, you can reach a higher tier."
        elif overall_score >= 50:
            verdict = "Developing candidate"
            tone    = "Work on expanding your technical vocabulary and practise explaining concepts in detail."
        else:
            verdict = "Needs significant improvement"
            tone    = "Focus on building foundational knowledge and practise speaking answers aloud before interviews."

        general_feedback = (
            f"{verdict} for a {self.context.role} interview at {self.context.difficulty} difficulty. "
            f"{tone} "
            f"Attempted {len(qa_pairs)} question(s) with an average response score of {overall_score}/100."
        )

        # ── question_feedback list (matches QuestionFeedback schema) ──
        question_feedback = [
            {
                "question": s["question"],
                "answer":   s["answer"],
                "score":    s["score"],
                "feedback": s["feedback"],
            }
            for s in scored
        ]

        return {
            "overall_score":           overall_score,
            "technical_score":         technical_score,
            "communication_score":     communication_score,
            "answer_relevance":        answer_relevance,
            "strengths":               strengths[:4],
            "weaknesses":              weaknesses[:4],
            "question_feedback":       question_feedback,
            "improvement_suggestions": improvement_suggestions,
            "practice_areas":          practice_areas,
            "general_feedback":        general_feedback,
        }

    def _minimal_evaluation(self) -> dict:
        """Returned when the session ended with no answers submitted."""
        return {
            "overall_score":           0,
            "technical_score":         0,
            "communication_score":     0,
            "answer_relevance":        0,
            "strengths":               [],
            "weaknesses":              ["No answers were submitted during this session."],
            "question_feedback":       [],
            "improvement_suggestions": ["Complete at least one question before ending the session."],
            "practice_areas":          [self.context.role + " fundamentals"],
            "general_feedback":        "Session ended without any answers being recorded.",
        }
