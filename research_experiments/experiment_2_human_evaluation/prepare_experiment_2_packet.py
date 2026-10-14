"""
Prepares the 35-item Blinded Review Packet for Experiment 2:
Automated Scoring versus Human Reviewers (Pilot Study).

Guarantees:
- Strictly blinds human review templates (no automated scores included).
- Generates blank CSV templates for Reviewer 1 and Reviewer 2.
- Generates full anchor instruction guidelines for human annotators.
- Pre-computes and stores automated rubric baseline scores in a separate reference file.
"""

import os
import sys
import json
import csv
from typing import List, Dict, Any

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.rubric.config import ORDERED_CRITERIA_KEYS, RUBRIC_CRITERIA
from app.rubric.aggregator import TopicGroup
from app.rubric.evaluator import rubric_evaluator
from app.rubric.calculator import compute_rubric_assessment

OUTPUT_DIR = os.path.abspath(os.path.dirname(__file__))

# 35 Diverse Pilot Interview Items across all 6 roles and 3 difficulty levels
PILOT_ITEMS = [
    # Full Stack Engineer (Items 1-6)
    {
        "item_id": "PILOT-01",
        "role": "Full Stack Engineer",
        "role_key": "full_stack_engineer",
        "difficulty": "beginner",
        "question": "Explain how frontend components communicate with backend REST or GraphQL endpoints, and how client-server data contracts are maintained.",
        "candidate_answer": "In full stack applications, frontend components use the browser fetch API or Axios to make HTTP requests to REST endpoints using standard verbs like GET, POST, PUT, and DELETE. For GraphQL, all requests typically go to a single endpoint using POST with a query body. Client-server data contracts are maintained using JSON schemas or TypeScript interfaces shared between the client and server repos to prevent contract drift.",
        "expected_points": ["HTTP methods and status codes", "Payload validation and schemas", "Versioning strategies", "Error contracts"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-02",
        "role": "Full Stack Engineer",
        "role_key": "full_stack_engineer",
        "difficulty": "intermediate",
        "question": "Describe how you design API contracts and handle contract drift between rapidly changing frontend code and backend microservices.",
        "candidate_answer": "We enforce contract-first development using OpenAPI specifications. Before writing backend code, we define the schema and generate TypeScript client types automatically. When backend changes are needed, we use semantic versioning on API routes like /v1 and /v2, maintaining backward compatibility for older clients. We also run automated contract tests in CI using tools like Pact to catch breaking schema changes before deployment.",
        "expected_points": ["Versioning strategies", "OpenAPI / schema generation", "Contract testing", "Backward compatibility"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-03",
        "role": "Full Stack Engineer",
        "role_key": "full_stack_engineer",
        "difficulty": "advanced",
        "question": "How do you architect distributed schema versioning, backward compatibility, and end-to-end type safety across separate frontend and backend deployments?",
        "candidate_answer": "We established an end-to-end type-safe architecture using Protocol Buffers and gRPC for backend microservices, and tRPC with OpenAPI for client boundaries. We treat schema deprecation with an additive-only policy: new fields are optional, and old fields are never deleted until telemetry shows zero client traffic for two release cycles. We also utilize a shared private npm package for generated TypeScript schemas synchronized via GitHub Actions.",
        "expected_points": ["Additive schema evolution", "Automated type generation", "Deprecation telemetry", "Distributed contract governance"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-04",
        "role": "Full Stack Engineer",
        "role_key": "full_stack_engineer",
        "difficulty": "beginner",
        "question": "What are the key differences between managing state on the client side versus caching data on the backend?",
        "candidate_answer": "Client state is stored in memory in the user's browser, like in React useState or Redux, and is lost when the page refreshes. Backend caching uses systems like Redis or Memcached to store shared data close to the server, reducing database load across all users.",
        "expected_points": ["Client memory vs server cache", "Persistence lifecycle", "Shared vs user-specific state"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-05",
        "role": "Full Stack Engineer",
        "role_key": "full_stack_engineer",
        "difficulty": "intermediate",
        "question": "How do you implement optimistic UI updates while ensuring database consistency and handling network rollback errors?",
        "candidate_answer": "I don't know the exact details, I think we just show the new state on the screen and hope the network doesn't fail.",
        "expected_points": ["Optimistic concurrency", "Rollback handling", "Cache snapshotting", "Error boundaries"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-06",
        "role": "Full Stack Engineer",
        "role_key": "full_stack_engineer",
        "difficulty": "advanced",
        "question": "Design a distributed cache invalidation strategy for a high-traffic full stack application with multi-layer caching (CDN, Redis, browser).",
        "candidate_answer": "We use a multi-tier cache invalidation pattern. At the edge CDN level, we set short Cache-Control max-age with stale-while-revalidate, and trigger programmatic cache tag purge calls upon database mutation. In Redis, we use explicit key deletion on write transactions accompanied by probabilistic early expiration (XFetch) to avoid cache stampede. On the browser, we use ETag validation.",
        "expected_points": ["Cache stampede mitigation", "Stale-while-revalidate", "Surrogate keys / cache tags", "Write-through vs write-delete"],
        "audio_present": False
    },

    # Frontend Developer (Items 7-12)
    {
        "item_id": "PILOT-07",
        "role": "Frontend Developer",
        "role_key": "frontend_developer",
        "difficulty": "beginner",
        "question": "How does the JavaScript event loop handle macrotasks versus microtasks when promises and timers resolve?",
        "candidate_answer": "The event loop has a call stack, a microtask queue, and a macrotask queue. Microtasks include promise callbacks (then, catch) and queueMicrotask. Macrotasks include setTimeout, setInterval, and I/O events. When the call stack is empty, the event loop drains the entire microtask queue before taking the next single macrotask from the macrotask queue.",
        "expected_points": ["Call stack and task queue", "Microtasks vs macrotasks", "Frame rendering lifecycle", "Queue drainage order"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-08",
        "role": "Frontend Developer",
        "role_key": "frontend_developer",
        "difficulty": "intermediate",
        "question": "Suppose a user rapidly changes search filters triggering multiple asynchronous fetch requests. How do you prevent stale responses from overwriting newer results?",
        "candidate_answer": "We use the browser AbortController API. Each time the search filter input changes, we abort the previous in-flight request before initiating the new fetch. Alternatively, in React libraries like TanStack Query or with a useRef counter, we track a monotonic request ID and discard any resolving responses whose ID is older than the current active query counter.",
        "expected_points": ["AbortController cancellation", "Race condition mitigation", "Stale response filtering", "Debounce/throttle"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-09",
        "role": "Frontend Developer",
        "role_key": "frontend_developer",
        "difficulty": "advanced",
        "question": "Explain the browser critical rendering path (DOM, CSSOM, Render Tree, Layout, Paint, Composite) and how GPU acceleration is utilized.",
        "candidate_answer": "The browser parses HTML to construct the DOM tree and parses CSS to construct the CSSOM tree. These are combined into the Render Tree, which contains visible nodes. Layout computes the geometric dimensions and positions of each box. Paint fills in pixels, colors, text, and borders. Finally, Composite draws layers onto the screen. By animating CSS transforms and opacity instead of top/left, the browser bypasses Layout and Paint entirely, handing layer compositing directly to the GPU.",
        "expected_points": ["Critical rendering path", "Layout thrashing prevention", "GPU composite layers", "Transforms vs layout mutations"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-10",
        "role": "Frontend Developer",
        "role_key": "frontend_developer",
        "difficulty": "beginner",
        "question": "What are Largest Contentful Paint (LCP) and Cumulative Layout Shift (CLS), and why do they matter to users?",
        "candidate_answer": "LCP measures how long it takes for the largest visual element on the screen to render. CLS measures unexpected shifting of elements during loading. They matter because users get frustrated if pages take forever to appear or if buttons jump around while clicking.",
        "expected_points": ["Core Web Vitals definitions", "User experience impact", "Layout stability"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-11",
        "role": "Frontend Developer",
        "role_key": "frontend_developer",
        "difficulty": "intermediate",
        "question": "How do you build a fully accessible modal dialog with focus trapping, escape key dismissal, and screen reader announcements?",
        "candidate_answer": "You put role='dialog' and aria-modal='true'. Then add an event listener for KeyDown to close it if escape is pressed.",
        "expected_points": ["Focus trapping mechanics", "Escape key dismissal", "ARIA attributes", "Return focus to trigger"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-12",
        "role": "Frontend Developer",
        "role_key": "frontend_developer",
        "difficulty": "advanced",
        "question": "Evaluate the architectural tradeoffs between streaming SSR with Suspense and static edge generation for a high-traffic e-commerce application.",
        "candidate_answer": "Static edge generation gives near-instant TTFB (sub-50ms) because HTML is served from global CDN PoPs. However, for personalized e-commerce pages with user cart state and dynamic pricing, pure static generation forces client-side waterfalls. Streaming SSR with React Suspense is the superior tradeoff: the outer page shell streams immediately from edge workers, while slow personalized blocks stream in as chunks resolve, preventing slow database calls from blocking TTFB.",
        "expected_points": ["TTFB vs personalization", "Streaming chunked transfer", "Edge rendering tradeoffs", "Suspense hydration"],
        "audio_present": False
    },

    # Backend Engineer (Items 13-18)
    {
        "item_id": "PILOT-13",
        "role": "Backend Engineer",
        "role_key": "backend_engineer",
        "difficulty": "beginner",
        "question": "What are the fundamental constraints of RESTful APIs, and what makes an API truly idempotent?",
        "candidate_answer": "REST requires client-server separation, statelessness, cacheability, uniform interface, and layered architecture. An idempotent API is one where making the same request multiple times produces the identical server state as making it once. GET, PUT, and DELETE are idempotent by HTTP specification, whereas POST is not.",
        "expected_points": ["Statelessness and uniform interface", "Idempotency definition", "HTTP verbs behavior", "Side-effect guarantees"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-14",
        "role": "Backend Engineer",
        "role_key": "backend_engineer",
        "difficulty": "intermediate",
        "question": "Explain the difference between Read Committed, Repeatable Read, and Serializable isolation levels, and what anomalies each prevents.",
        "candidate_answer": "Read Committed prevents dirty reads by only reading committed data, but allows non-repeatable reads. Repeatable Read ensures that repeated reads within the same transaction see identical snapshot rows, preventing dirty reads and non-repeatable reads. Serializable is the strictest level, preventing all anomalies including phantom reads and write skew by enforcing an execution order equivalent to serial execution, usually using two-phase locking or SSI.",
        "expected_points": ["Dirty reads and non-repeatable reads", "Phantom reads and write skew", "Snapshot isolation vs 2PL", "Performance tradeoffs"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-15",
        "role": "Backend Engineer",
        "role_key": "backend_engineer",
        "difficulty": "advanced",
        "question": "Two concurrent backend threads attempt to withdraw funds from the same account balance simultaneously. Walk through row-level locking vs optimistic concurrency control.",
        "candidate_answer": "In row-level pessimistic locking, the first thread executes SELECT balance FROM accounts WHERE id = ? FOR UPDATE. The database engine acquires an exclusive row lock, forcing the second thread to block until the first commits or rolls back, preventing lost updates. In optimistic concurrency control (OCC), each row has a version integer. Threads read without locks, and write using UPDATE accounts SET balance = ?, version = version + 1 WHERE id = ? AND version = @old_version. If 0 rows are updated, the conflict is caught and retried. Pessimistic is better under high contention; OCC is better under low contention.",
        "expected_points": ["SELECT FOR UPDATE mechanics", "Version column and compare-and-swap", "Contention tradeoffs", "Deadlock handling"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-16",
        "role": "Backend Engineer",
        "role_key": "backend_engineer",
        "difficulty": "beginner",
        "question": "What is connection pooling, and why shouldn't every incoming HTTP request open a new raw database connection?",
        "candidate_answer": "Opening a database connection requires a TCP handshake, TLS negotiation, authentication, and allocating backend server memory. A connection pool keeps a set of active connections open, reusing them across incoming HTTP requests and drastically reducing latency.",
        "expected_points": ["Connection lifecycle overhead", "Reuse mechanics", "Database server resource protection"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-17",
        "role": "Backend Engineer",
        "role_key": "backend_engineer",
        "difficulty": "intermediate",
        "question": "How do you guarantee at-least-once message delivery in message brokers like RabbitMQ or Kafka, and how do you ensure idempotent message processing?",
        "candidate_answer": "We just turn on acknowledgments in Kafka and the messages don't get lost.",
        "expected_points": ["Consumer acknowledgments", "Idempotency keys and deduplication tables", "At-least-once vs exactly-once", "Dead-letter handling"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-18",
        "role": "Backend Engineer",
        "role_key": "backend_engineer",
        "difficulty": "advanced",
        "question": "Evaluate the Redlock algorithm versus database-level advisory locks: under what circumstances can distributed locking lead to split-brain or data corruption?",
        "candidate_answer": "Martin Kleppmann demonstrated that Redlock relies on synchrony assumptions that fail in real distributed systems: long garbage collection pauses or process descheduling can cause a node's lock lease to expire while it still believes it owns the lock. If another node acquires the lock, both mutate shared state simultaneously. To safely use distributed locks, downstream resources must enforce fencing tokens (monotonically increasing version numbers) that reject writes with older tokens. Postgres advisory locks avoid this by bounding the lock lifecycle to an active TCP connection or transaction.",
        "expected_points": ["Lease expiration during GC pauses", "Fencing tokens requirement", "Kleppmann vs Redlock", "Postgres advisory lock semantics"],
        "audio_present": False
    },

    # DevOps / SRE (Items 19-24)
    {
        "item_id": "PILOT-19",
        "role": "DevOps / SRE",
        "role_key": "devops_sre",
        "difficulty": "beginner",
        "question": "How do Linux namespaces and cgroups provide isolation for Docker containers compared to virtual machines?",
        "candidate_answer": "Namespaces provide isolation of system views like PID, mount points, networking, IPC, and user IDs, making a process believe it is running in its own OS. Cgroups constrain and monitor resource usage like CPU quotas, memory limits, and I/O bandwidth. Unlike VMs, containers share the host Linux kernel, eliminating hypervisor overhead.",
        "expected_points": ["Linux namespaces types", "Cgroups resource quotas", "Shared kernel vs hypervisor", "Security isolation boundaries"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-20",
        "role": "DevOps / SRE",
        "role_key": "devops_sre",
        "difficulty": "intermediate",
        "question": "Explain how Kubernetes readiness and liveness probes operate, and what happens if a readiness probe fails under heavy traffic.",
        "candidate_answer": "Liveness probes check if a container is running; if it fails, kubelet restarts the container. Readiness probes check if the container is ready to accept traffic; if it fails, Kubernetes removes the pod IP from the Service endpoints so no new requests are routed to it. If readiness probes fail under heavy traffic, pods get pulled from the load balancer, cascading traffic to remaining pods and causing full cluster collapse.",
        "expected_points": ["Liveness restart vs readiness endpoint removal", "Cascading failure mode under load", "Health check timeouts and thresholds", "Probe configuration best practices"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-21",
        "role": "DevOps / SRE",
        "role_key": "devops_sre",
        "difficulty": "advanced",
        "question": "Walk through the termination lifecycle of a Kubernetes pod: how do you ensure zero dropped connections during rolling updates using preStop hooks and terminationGracePeriodSeconds?",
        "candidate_answer": "When a pod is deleted, two asynchronous actions occur: the pod is marked Terminating and removed from Service endpoints by kube-proxy/iptables, while kubelet executes the preStop hook. Because endpoint propagation across nodes takes several seconds, without a preStop hook the container might shut down immediately while in-flight requests are still in transit. We add a preStop sleep of 15 seconds to allow load balancers to drain, then the app handles SIGTERM gracefully before terminationGracePeriodSeconds expires.",
        "expected_points": ["Asynchronous endpoint removal", "preStop hook sleep pattern", "SIGTERM vs SIGKILL", "Graceful connection draining"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-22",
        "role": "DevOps / SRE",
        "role_key": "devops_sre",
        "difficulty": "beginner",
        "question": "What is the difference between an SLA, an SLO, and an SLI?",
        "candidate_answer": "An SLI is a Service Level Indicator, which is a measurable metric like latency or error rate. An SLO is a Service Level Objective, which is the internal target we aim for, like 99.9% uptime. An SLA is a Service Level Agreement, which is the legal contract with customers with financial penalties if breached.",
        "expected_points": ["SLI measurement definition", "SLO internal target", "SLA commercial contract"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-23",
        "role": "DevOps / SRE",
        "role_key": "devops_sre",
        "difficulty": "intermediate",
        "question": "How do you manage remote state, state locking, and secret isolation when multiple DevOps engineers work with Terraform simultaneously?",
        "candidate_answer": "We keep terraform.tfstate in Git so everyone can pull it before applying.",
        "expected_points": ["Remote backend (S3 / GCS)", "State locking (DynamoDB)", "Secret exposure risks in state files", "Blast radius isolation"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-24",
        "role": "DevOps / SRE",
        "role_key": "devops_sre",
        "difficulty": "advanced",
        "question": "Evaluate Recovery Time Objective (RTO) versus Recovery Point Objective (RPO) when designing a cross-region disaster recovery architecture for a mission-critical platform.",
        "candidate_answer": "RPO defines maximum tolerable data loss in time, dictating replication strategy: synchronous replication achieves near-zero RPO but incurs network latency penalties across regions, whereas asynchronous replication avoids write latency at the cost of potential data loss during sudden regional failure. RTO defines maximum tolerable downtime before services are restored: active-active multi-region achieves sub-minute RTO via DNS health check failover but carries high architectural complexity and cross-region consensus costs.",
        "expected_points": ["RPO data loss vs replication mode", "RTO downtime vs failover automation", "Active-active vs active-passive cost trade-offs", "Cross-region network latency constraints"],
        "audio_present": False
    },

    # ML Engineer (Items 25-30)
    {
        "item_id": "PILOT-25",
        "role": "ML Engineer",
        "role_key": "ml_engineer",
        "difficulty": "beginner",
        "question": "Why is it critical to fit feature transformers (like scalers or encoders) on training data only rather than the entire dataset?",
        "candidate_answer": "Fitting scalers or encoders on the entire dataset causes data leakage. Information from the validation and test sets (such as global mean, variance, or unseen categorical distributions) leaks into the training pipeline, artificially inflating validation metrics and leading to poor generalization in real-world deployment.",
        "expected_points": ["Data leakage mechanism", "Validation score inflation", "Generalization degradation", "Pipeline encapsulation"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-26",
        "role": "ML Engineer",
        "role_key": "ml_engineer",
        "difficulty": "intermediate",
        "question": "What is training-serving skew (parity drift), and how do feature stores (like Feast) prevent online features from diverging from offline training features?",
        "candidate_answer": "Training-serving skew occurs when the code or data definitions used to compute features during offline training differ from the real-time feature computation at inference time. Feature stores centralize feature definitions as code, maintaining a dual-store architecture: an offline columnar store for point-in-time correct training generation, and a low-latency key-value cache (Redis) for real-time online feature lookups, guaranteeing 100% mathematical parity.",
        "expected_points": ["Training-serving skew causes", "Point-in-time correct joins", "Dual store (offline vs online)", "Feature definitions as code"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-27",
        "role": "ML Engineer",
        "role_key": "ml_engineer",
        "difficulty": "advanced",
        "question": "When ground-truth labels are delayed by weeks (e.g., credit fraud or loan default), how do you monitor and estimate model degradation in real time?",
        "candidate_answer": "When labels are delayed, you cannot calculate real-time precision or recall. Instead, we monitor input data drift and output prediction drift. We run statistical tests like Population Stability Index (PSI) and Wasserstein distance on input features, alerting if PSI exceeds 0.2. We also track the model prediction distribution (e.g. average score, logits variance) and compare against baseline. If predictions shift significantly while inputs drift, degradation is inferred before ground truth arrives.",
        "expected_points": ["Delayed feedback challenge", "Input covariate shift (PSI / KS)", "Prediction distribution drift", "Proxy metrics and alerting"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-28",
        "role": "ML Engineer",
        "role_key": "ml_engineer",
        "difficulty": "beginner",
        "question": "Why is accuracy a misleading metric for highly imbalanced classification datasets, and what should you use instead?",
        "candidate_answer": "If 99% of transactions are legitimate and 1% are fraud, a dummy model that always predicts legitimate gets 99% accuracy while catching zero fraud. Instead, you should evaluate Precision, Recall, F1-score, or the Area Under the Precision-Recall Curve (PR-AUC).",
        "expected_points": ["Majority class bias in accuracy", "PR-AUC and F1-score alternatives", "Business impact of false negatives"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-29",
        "role": "ML Engineer",
        "role_key": "ml_engineer",
        "difficulty": "intermediate",
        "question": "What statistical tests (KS test, PSI, Wasserstein distance) do you run on input features to detect data drift before model accuracy drops?",
        "candidate_answer": "We just look at a histogram in a notebook once every few months.",
        "expected_points": ["Kolmogorov-Smirnov test mechanics", "Population Stability Index thresholds", "Automated drift pipelines", "Continuous monitoring"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-30",
        "role": "ML Engineer",
        "role_key": "ml_engineer",
        "difficulty": "advanced",
        "question": "Evaluate the architectural tradeoffs between deploying a large foundation model vs distilling it into a lightweight student model for high-throughput production.",
        "candidate_answer": "Large foundation models offer high zero-shot quality and nuanced reasoning, but impose massive GPU memory footprint, high p99 latency (often 500ms to 2s), and expensive inference hardware costs. In contrast, distilling task-specific knowledge into a lightweight student model (like a 4-layer transformer or quantized CNN) compresses parameters by 10x, drops latency to sub-20ms on commodity CPUs, and scales cost-effectively. The tradeoff is reduced generalized reasoning on out-of-domain edge cases.",
        "expected_points": ["Knowledge distillation mechanics", "Latency and throughput budgets", "Hardware cost (GPU vs CPU)", "Out-of-domain generalization loss"],
        "audio_present": False
    },

    # Data Analyst (Items 31-35)
    {
        "item_id": "PILOT-31",
        "role": "Data Analyst",
        "role_key": "data_analyst",
        "difficulty": "beginner",
        "question": "How does SQL handle NULL values in conditional WHERE clauses and aggregate functions like COUNT(col) vs COUNT(*)?",
        "candidate_answer": "SQL uses three-valued logic where comparisons with NULL evaluate to UNKNOWN, which WHERE clauses treat as false. Aggregate functions like COUNT(column_name) ignore NULL values, only counting rows with non-null values in that column. In contrast, COUNT(*) counts all rows in the table or group, including rows where some or all columns are NULL.",
        "expected_points": ["Three-valued logic (UNKNOWN)", "COUNT(*) vs COUNT(col)", "WHERE clause filtering of NULLs", "COALESCE handling"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-32",
        "role": "Data Analyst",
        "role_key": "data_analyst",
        "difficulty": "intermediate",
        "question": "What is aggregation grain, and how does grouping by the wrong level of detail lead to double-counting in business reports?",
        "candidate_answer": "Aggregation grain refers to what a single row represents in a dataset, such as one transaction, one user per day, or one store. When you join tables with different grains, like joining an orders table to an order_items table on order_id, the order-level fields (like shipping fee or order total) are duplicated across every item row. Summing the order total directly on the joined table results in severe double-counting.",
        "expected_points": ["Aggregation grain definition", "One-to-many join fan-out", "Double-counting metrics risk", "Pre-aggregation mitigation"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-33",
        "role": "Data Analyst",
        "role_key": "data_analyst",
        "difficulty": "advanced",
        "question": "Explain Simpson's Paradox: how can a trend appear across multiple customer segments but reverse when the data is aggregated together?",
        "candidate_answer": "Simpson's Paradox occurs when a statistical trend observed within several distinct subgroups disappears or reverses when the groups are combined. This is caused by a confounding variable and unequal group sample distributions. For example, feature adoption might have a higher conversion rate for both desktop users and mobile users individually, but if mobile users have an overall much lower conversion rate and make up 90% of the new feature test group, the aggregate result will falsely suggest the feature hurt conversions.",
        "expected_points": ["Confounding variables", "Unequal subgroup weighting", "Reversal of causal direction", "Stratified analysis mitigation"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-34",
        "role": "Data Analyst",
        "role_key": "data_analyst",
        "difficulty": "beginner",
        "question": "Why is the median often a better summary metric than the mean for skewed distributions like user income or session duration?",
        "candidate_answer": "The mean is heavily influenced by extreme outliers, like a few billionaires pulling up average income. The median represents the exact 50th percentile and is robust to outliers, giving a much more accurate reflection of a typical user's experience.",
        "expected_points": ["Outlier sensitivity of mean", "Robustness of median", "Skewed distribution properties"],
        "audio_present": False
    },
    {
        "item_id": "PILOT-35",
        "role": "Data Analyst",
        "role_key": "data_analyst",
        "difficulty": "intermediate",
        "question": "What is the purpose of an A/B test, and what does a p-value of 0.03 tell you in business terms?",
        "candidate_answer": "A p-value of 0.03 means there is a 97% chance the feature works and will increase revenue.",
        "expected_points": ["Null hypothesis definition", "p-value interpretation (probability of observing result under null)", "Common misconception identification", "Statistical significance threshold"],
        "audio_present": False
    }
]


def generate_blinded_review_packet():
    """Generates the blinded JSON packet for reviewers."""
    blinded_items = []
    for item in PILOT_ITEMS:
        blinded_items.append({
            "item_id": item["item_id"],
            "role": item["role"],
            "difficulty": item["difficulty"],
            "question": item["question"],
            "candidate_answer": item["candidate_answer"],
            "eligible_criteria": [
                "technical_knowledge",
                "problem_solving",
                "practical_application",
                "relevance_completeness",
                "communication_clarity",
                "followup_reflection"
            ]
        })
    
    packet_path = os.path.join(OUTPUT_DIR, "blinded_review_packet.json")
    with open(packet_path, "w", encoding="utf-8") as f:
        json.dump({
            "study_title": "PreMock AI Pilot Study: Human vs Automated Rubric Agreement",
            "rubric_version": "interview_practice_100_v1",
            "total_items": len(blinded_items),
            "instructions": "Assign integer anchors (0, 1, 2, 3, or 4) for each eligible criterion based on the rubric guidelines.",
            "items": blinded_items
        }, f, indent=2)
    print(f"Blinded review packet written to: {packet_path}")


def generate_blank_review_templates():
    """Generates blank CSV scoring templates for Reviewer 1 and Reviewer 2."""
    fieldnames = [
        "item_id", "role", "difficulty",
        "technical_knowledge", "problem_solving", "practical_application",
        "relevance_completeness", "communication_clarity", "followup_reflection",
        "spoken_delivery", "reviewer_notes"
    ]
    
    for r_num in (1, 2):
        csv_path = os.path.join(OUTPUT_DIR, f"review_scoring_template_reviewer{r_num}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in PILOT_ITEMS:
                writer.writerow({
                    "item_id": item["item_id"],
                    "role": item["role"],
                    "difficulty": item["difficulty"],
                    "technical_knowledge": "",
                    "problem_solving": "",
                    "practical_application": "",
                    "relevance_completeness": "",
                    "communication_clarity": "",
                    "followup_reflection": "",
                    "spoken_delivery": "N/A (Text-Only)",
                    "reviewer_notes": ""
                })
        print(f"Blank review template for Reviewer {r_num} written to: {csv_path}")


def generate_automated_scores_reference():
    """Computes automated scores for the 35 pilot items as the reference benchmark."""
    auto_records = []
    
    for item in PILOT_ITEMS:
        # Construct topic group
        tg = TopicGroup(
            group_id=item["item_id"],
            title=f"{item['role']} - {item['difficulty']}",
            phase="technical",
            main_question=item["question"],
            main_answer=item["candidate_answer"],
            followups=[],
            revisions=[],
            eligible_criteria=[
                "technical_knowledge", "problem_solving", "practical_application",
                "relevance_completeness", "communication_clarity", "followup_reflection"
            ],
            has_audio=False
        )
        
        # Evaluate group
        group_eval = rubric_evaluator.evaluate_topic_group(
            group=tg,
            job_role=item["role"],
            difficulty=item["difficulty"],
            expected_points=item.get("expected_points", [])
        )
        
        ratings = group_eval.get("ratings", {})
        
        # Compute overall assessment
        assessment = compute_rubric_assessment(ratings)
        
        auto_records.append({
            "item_id": item["item_id"],
            "role": item["role"],
            "difficulty": item["difficulty"],
            "ratings": ratings,
            "assessed_score": assessment["assessed_score"],
            "assessed_maximum": assessment["assessed_maximum"],
            "provisional_normalized_100": assessment["provisional_normalized_100"]
        })
    
    ref_path = os.path.join(OUTPUT_DIR, "automated_scores_blinded_reference.json")
    with open(ref_path, "w", encoding="utf-8") as f:
        json.dump(auto_records, f, indent=2)
    print(f"Automated reference scores written to: {ref_path}")


def generate_instructions_markdown():
    """Generates the full human reviewer instructions markdown document."""
    doc = f"""# Human Reviewer Instructions: Interview Rubric Evaluation (Pilot Study)

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
"""
    instr_path = os.path.join(OUTPUT_DIR, "review_packet_instructions.md")
    with open(instr_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Instructions guide written to: {instr_path}")


if __name__ == "__main__":
    generate_blinded_review_packet()
    generate_blank_review_templates()
    generate_automated_scores_reference()
    generate_instructions_markdown()
    print("All Experiment 2 packets and templates generated successfully.")
