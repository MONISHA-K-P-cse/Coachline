import logging

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve

logger = logging.getLogger("roadmap_agent")


class RoadmapAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_roadmap(
        self,
        target_role: str,
        current_skills: str,
        target_company: str = "",
        experience_level: str = "",
        weeks: int = 8,
        jd_summary: str = "",
        learning_style: str = "",
    ):
        context = "\n\n".join(retrieve(target_role, k=3))

        profile_lines = [f"Target Role:\n{target_role}"]
        if target_company:
            profile_lines.append(f"Target Company:\n{target_company}")
        if experience_level:
            profile_lines.append(f"Candidate Experience Level:\n{experience_level}")
        if learning_style:
            profile_lines.append(f"Preferred Learning Style:\n{learning_style}")
        if jd_summary:
            profile_lines.append(f"Job Description Analysis & Identified Gaps:\n{jd_summary}")

        profile_block = "\n\n".join(profile_lines)

        prompt = f"""
You are an expert software mentor and curriculum architect.

{profile_block}

Current Skills:
{current_skills}

Reference Material (only use if relevant to the Target Role above):
{context}

Create a PRECISE, UNIQUE, {weeks}-week learning roadmap deeply tailored to the candidate's target role ({target_role}), experience level ({experience_level or 'Standard'}), and target company ({target_company or 'Top Tech Standards'}):

CRITICAL GUIDELINES:
1. NO DUPLICATE TITLES: Every week MUST have a completely distinct, unique, highly specific title card reflecting a distinct milestone for that week.
2. TAILORING: Customize the topics specifically to {target_role} and {target_company or 'industry expectations'}.
3. SYLLABUS: For each step, provide a detailed "syllabus" list of 3-5 subtopics.
4. PRACTICE QUESTIONS: For each step, provide AT LEAST 5 practice questions derived directly from the step's syllabus subtopics.

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no commentary.

Schema:
{{
  "steps": [
    {{
      "title": <string, distinct title for Week 1>, 
      "description": <string, 1-3 sentences>, 
      "estimated_hours": <integer>,
      "syllabus": [<string subtopic 1>, <string subtopic 2>, <string subtopic 3>],
      "questions": [<string question 1>, <string question 2>, <string question 3>, <string question 4>, <string question 5>]
    }},
    ...
  ]
}}

Produce exactly {weeks} entries in "steps", one per week, in week order. Ensure NO TWO STEPS SHARE THE SAME TITLE.
"""

        raw = self.client.generate(prompt)
        return self._convert_to_schema(raw, target_role, target_company, experience_level, weeks, jd_summary)

    def _get_role_customized_fallback_steps(
        self,
        target_role: str,
        target_company: str,
        experience_level: str,
        weeks: int,
        jd_summary: str = "",
    ) -> list:
        role_lower = target_role.lower()
        comp_str = f" @ {target_company}" if target_company else ""

        if "frontend" in role_lower or "react" in role_lower or "ui" in role_lower or "web" in role_lower:
            themes = [
                ("Modern JavaScript/TypeScript Deep Dive", ["DOM Events & Performance", "TypeScript Generics & Types", "Async/Await & Event Loop", "Memory Management"]),
                ("Advanced React Patterns & Custom Hooks", ["Custom Hooks Architecture", "Compound Components", "State Management Strategies", "Re-render Optimization"]),
                ("State Management & Global Application Store", ["Redux Toolkit / Zustand", "Context API vs Store", "Normalized State Trees", "Side Effect Middleware"]),
                ("Web Performance & Core Web Vitals", ["Code Splitting & Lazy Loading", "LCP, CLS & INP Optimization", "Asset Bundling & Compression", "Browser Rendering Pipeline"]),
                ("CSS Architecture & Responsive Systems", ["Tailwind / CSS Modules", "Design Tokens", "Accessibility (a11y) Standards", "Theme Switching"]),
                ("Browser APIs, Storage & Service Workers", ["IndexedDB & LocalStorage", "Service Workers & PWA", "Fetch/Axios Abstractions", "WebSockets & SSE"]),
                ("Testing, CI/CD & Frontend Security", ["Jest & React Testing Library", "E2E with Playwright/Cypress", "XSS & CSRF Prevention", "Content Security Policy"]),
                (f"Staff Frontend Architecture & {target_company or 'System'} Design", ["Micro-frontends Architecture", "Monorepo Setup (Turborepo)", "SSR & Hydration Strategies", "Mock Interview Loop"])
            ]
        elif "data" in role_lower or "machine learning" in role_lower or "ai" in role_lower or "ml" in role_lower:
            themes = [
                ("Data Pipeline Engineering & ETL Architectures", ["Spark & PySpark Fundamentals", "Batch vs Streaming Data", "Schema Evolution", "Data Lakehouse Setup"]),
                ("Advanced Database Querying & SQL Optimization", ["Complex Joins & Window Functions", "Query Execution Plans", "Indexing & Partitioning", "Columnar vs Row Storage"]),
                ("Feature Engineering & Model Pipeline Setup", ["Data Preprocessing", "Feature Stores (Feast)", "Vector Embeddings & RAG", "Dimensionality Reduction"]),
                ("Distributed Computing & Large-Scale Processing", ["Distributed Storage (S3/HDFS)", "MapReduce Concepts", "Dask & Ray Orchestration", "Resource Allocation"]),
                ("Model Evaluation, MLOps & Experiment Tracking", ["MLflow & Weights & Biases", "Model Monitoring & Drift", "CI/CD for ML Models", "A/B Testing Frameworks"]),
                ("Vector Databases & RAG Search Retrieval", ["ChromaDB & FAISS Vector Indexing", "Embedding Models", "Hybrid Search", "Prompt Engineering"]),
                ("Data Governance, Quality & Pipeline Reliability", ["Great Expectations", "Data Lineage & Metadata", "SLA & Error Budgeting", "Data Security & Anonymization"]),
                (f"AI System Design for {target_company or 'Enterprise Scale'}", ["Scalable Real-time Recommendation Engine", "LLM Serving Infrastructure", "Distributed Model Training", "Mock Interview Loop"])
            ]
        elif "devops" in role_lower or "cloud" in role_lower or "sre" in role_lower or "infrastructure" in role_lower:
            themes = [
                ("Infrastructure as Code (IaC) & Cloud Provisioning", ["Terraform Modules & State", "AWS/GCP Architecture", "Cloud Networking & VPCs", "IAM Policies"]),
                ("Containerization & Docker Image Optimization", ["Multi-stage Docker Builds", "Container Security Scanning", "Docker Compose", "Resource Limits"]),
                ("Kubernetes Orchestration & Helm Deployment", ["Pods, Services & Ingress", "StatefulSets vs Deployments", "Helm Chart Templating", "Cluster Autoscaling"]),
                ("CI/CD Pipeline Automation & GitOps", ["GitHub Actions / GitLab CI", "ArgoCD / Flux GitOps", "Canary & Blue-Green Deployments", "Automated Rollbacks"]),
                ("Observability, Telemetry & Incident Management", ["Prometheus & Grafana Alerting", "OpenTelemetry Tracing", "ELK/LOKI Log Aggregation", "On-Call & Post-mortems"]),
                ("Cloud Security, Secret Management & Compliance", ["HashiCorp Vault Integration", "TLS/SSL Certificate Management", "Network Security Groups", "SOC2 Compliance"]),
                ("High Availability, Chaos Engineering & Disaster Recovery", ["Multi-Region Failover", "Chaos Mesh & Fault Injection", "RTO & RPO Targets", "Backup Automation"]),
                (f"Infrastructure System Design for {target_company or 'Enterprise Scale'}", ["Global Traffic Load Balancing", "Zero-Downtime Migration", "Cost Optimization Strategies", "Mock Interview Loop"])
            ]
        else:
            themes = [
                ("Domain Modeling, Clean Architecture & API Contracts", ["RESTful API Specification", "gRPC & Protocol Buffers", "Domain-Driven Design (DDD)", "Database Schema Design"]),
                ("Advanced Relational & NoSQL Database Engineering", ["PostgreSQL Indexing & Transactions", "Query Cost Analysis", "Sharding & Partitioning", "Redis Caching Strategies"]),
                ("Distributed Systems, Microservices & Messaging", ["Message Queues (Kafka/RabbitMQ)", "Event-Driven Architectures", "Idempotency & Retry Loops", "Saga Pattern for Transactions"]),
                ("High-Throughput Caching & Rate Limiting Systems", ["Redis Cluster Setup", "Distributed Rate Limiters", "Cache Eviction Policies", "Cache Stampede Mitigation"]),
                ("Concurrency, Asynchronous Processing & Thread Pools", ["Event Loop Architecture", "Async/Await Internals", "Worker Pool Queue Management", "Race Condition Lock Controls"]),
                ("System Reliability, Resiliency & Graceful Degradation", ["Circuit Breaker Pattern", "Bulkhead Isolation", "Health Checks & Graceful Shutdown", "Fallback Mechanism Design"]),
                ("Observability, Distributed Tracing & Security Auditing", ["OpenTelemetry & Jaeger Tracing", "Structured Logging (JSON)", "JWT Auth & Role-Based Access", "OWASP Security Standards"]),
                (f"Staff System Design & {target_company or 'Company'} Architecture Loop", ["Global Scale Distributed Cache", "Payment Processing Engine", "Real-Time Infrastructure", "Mock Interview Loop"])
            ]

        steps = []
        for i in range(weeks):
            theme_idx = i % len(themes)
            title_base, default_syllabus = themes[theme_idx]
            cycle_suffix = f" - Phase {i // len(themes) + 1}" if i >= len(themes) else ""
            title = f"{title_base}{cycle_suffix}"

            company_note = f" (Tailored for {target_company})" if target_company else ""
            desc = f"Master {title_base.lower()}{company_note}. Focus on practical implementation trade-offs, high-scale scenarios, and interview criteria for {target_role}."

            questions = [
                f"How would you architect and implement {title_base} in a production {target_role} service{company_note}?",
                f"What are the primary trade-offs, bottlenecks, and failure modes when working with {default_syllabus[0]}?",
                f"Explain how you would monitor, debug, and optimize performance for {default_syllabus[1]}.",
                f"How do you handle scaling and reliability challenges related to {default_syllabus[2]}?",
                f"Compare standard industry approaches for {default_syllabus[3]} and justify your architectural choice."
            ]

            steps.append({
                "step_number": i + 1,
                "title": title,
                "description": desc,
                "estimated_hours": 20 + (i % 3) * 5,
                "syllabus": default_syllabus,
                "questions": questions,
                "notes": f"Focus on mastering {title_base}. Understand theoretical trade-offs, standard architectures, and key questions asked at {target_company or 'top tech companies'}.",
                "status": "pending"
            })

        return steps

    def _convert_to_schema(
        self,
        raw: str,
        target_role: str,
        target_company: str,
        experience_level: str,
        weeks: int,
        jd_summary: str = "",
    ):
        try:
            data = extract_json(raw)
            raw_steps = data.get("steps", [])
            if not raw_steps or len(raw_steps) == 0:
                raise ValueError("LLM returned zero roadmap steps")

            seen_titles = set()
            steps = []
            fallback_list = self._get_role_customized_fallback_steps(target_role, target_company, experience_level, weeks, jd_summary)

            for i, s in enumerate(raw_steps):
                if i >= weeks:
                    break

                raw_title = str(s.get("title", "")).strip()
                # Deduplicate and refine titles to prevent duplicate title cards across weeks
                if not raw_title or raw_title in seen_titles or raw_title.lower().startswith("week "):
                    title = fallback_list[i % len(fallback_list)]["title"]
                else:
                    title = raw_title

                seen_titles.add(title)
                desc = str(s.get("description", "")).strip()
                syllabus = [str(x).strip() for x in s.get("syllabus", []) if x]
                if not syllabus:
                    syllabus = [t.strip() for t in desc.split(",") if t.strip()] or [f"{title} Fundamentals", f"{title} Architecture", f"{title} Best Practices"]

                questions = [str(q).strip() for q in s.get("questions", []) if q]
                if len(questions) < 5:
                    fallback_qs = [
                        f"What are the core principles and architectural trade-offs of {title}?",
                        f"How would you troubleshoot and resolve performance bottlenecks in {title}?",
                        f"Explain how {syllabus[0] if syllabus else title} operates under high scale.",
                        f"What are the common failure modes and security best practices for {title}?",
                        f"Compare and contrast key approaches when implementing {syllabus[-1] if syllabus else title}."
                    ]
                    for fq in fallback_qs:
                        if fq not in questions and len(questions) < 5:
                            questions.append(fq)

                steps.append({
                    "step_number": i + 1,
                    "title": title,
                    "description": desc or f"Deep dive into {title} concepts and production architectures tailored for {target_role}.",
                    "estimated_hours": int(s.get("estimated_hours", 20)),
                    "questions": questions,
                    "syllabus": syllabus,
                    "notes": str(s.get("notes", "")).strip(),
                    "status": "pending",
                })

            # Fill up remaining steps if LLM returned fewer steps than requested weeks
            if len(steps) < weeks:
                for i in range(len(steps), weeks):
                    steps.append(fallback_list[i])

        except Exception as exc:
            logger.warning(
                "Roadmap agent JSON parse/validation failed for role '%s' (%s); using customized role steps",
                target_role,
                exc,
            )
            steps = self._get_role_customized_fallback_steps(target_role, target_company, experience_level, weeks, jd_summary)

        company_title_str = f" @ {target_company}" if target_company else ""
        return {
            "title": f"{target_role}{company_title_str} Preparation Roadmap",
            "target_role": target_role,
            "steps_json": steps,
            "progress_percentage": 0,
        }

    def generate_remediation_question(
        self,
        target_role: str,
        week: int,
        topic: str,
        syllabus: list,
        failed_question: str,
        user_answer: str,
        feedback: str,
    ) -> str:
        prompt = f"""You are an expert technical interviewer and educator.

Target Role: {target_role}
Week {week} Topic: {topic}
Syllabus Concepts: {', '.join(syllabus) if syllabus else topic}

The candidate scored LESS THAN 50% on the following practice question:
Practice Question: {failed_question}
Candidate's Answer: {user_answer}
Evaluation Feedback: {feedback}

Task: Generate ONE new, foundational practice question for Week {week} ({topic}) specifically designed to improve the candidate's understanding of the underlying concept they missed.

Respond ONLY with the text of the new practice question. Do not include quotes, prefix, markdown formatting, or explanations."""
        try:
            raw = self.client.generate(prompt)
            cleaned = raw.strip().strip('"').strip("'")
            if not cleaned or len(cleaned) < 10:
                cleaned = f"Foundational Refresher ({topic}): Can you explain the core concepts of {syllabus[0] if syllabus else topic} step-by-step?"
            return cleaned
        except Exception as exc:
            logger.warning("generate_remediation_question failed (%s); using fallback question", exc)
            return f"Foundational Refresher ({topic}): How does {syllabus[0] if syllabus else topic} work conceptually and what are its key components?"