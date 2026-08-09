import json
import re
import logging
from typing import List, Dict, Any, Optional
from ai.agents.granite_client import GraniteClient

logger = logging.getLogger("bob_coach_agent")

class BobCoachAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as e:
                logger.error("Failed to parse regex-extracted JSON: %s. Content: %s", e, text)
        try:
            return json.loads(text)
        except Exception as e:
            logger.error("Failed to parse raw JSON: %s. Content: %s", e, text)
            return {}

    def start_scenario(
        self,
        target_role: str,
        experience_level: str = "",
        resume_skills: str = "",
        weakness: str = "",
        mastery_summary: str = ""
    ) -> dict:
        """
        Generates the initial scenario based on candidate context.
        """
        prompt = f"""You are IBM Bob, a senior engineering scenario coach.
Your job is NOT to ask normal quiz questions. Instead, give the candidate a realistic, role-specific software engineering scenario where they must make trade-offs, choose architectures, and defend their choices.

Candidate context:
- Target Role: {target_role}
- Experience Level: {experience_level or "Mid-Level"}
- Resume/Skills: {resume_skills or "N/A"}
- Focus/Weakness Area: {weakness or "System Design & Architecture"}
- Topic Mastery Status: {mastery_summary or "N/A"}

Generate a challenging engineering scenario based on this context. 
If weakness is System Design, prioritize a scaling, database bottleneck, or high-throughput design issue.
If frontend, prioritize state, rendering performance, or architecture bottlenecks.

You must respond ONLY with a JSON object of the following format:
{{
  "next_question": "Scenario description and initial question here",
  "difficulty": "easy",
  "topic": "system_design",
  "reasoning_focus": "scalability"
}}

Do not include any conversational filler outside the JSON. Return valid JSON.
"""
        response = self.client.generate(prompt)
        parsed = self._extract_json(response)
        
        # Fallback if AI fails or returns empty
        if not parsed or "next_question" not in parsed:
            parsed = {
                "next_question": f"You are designing a system for {target_role}. As traffic grows, the main database experiences a heavy read bottleneck. How would you solve this?",
                "difficulty": "medium",
                "topic": "System Design",
                "reasoning_focus": "databases"
            }
        return parsed

    def respond_to_candidate(
        self,
        conversation_history: List[Dict[str, str]],
        candidate_response: str,
        target_role: str,
        difficulty: str
    ) -> dict:
        """
        Processes a turn. Bob challenges the candidate's technical choices (plays Devil's Advocate)
        and introduces constraints/adjusts difficulty based on answer quality.
        """
        history_formatted = ""
        for turn in conversation_history:
            sender = "Candidate" if turn["sender"] == "candidate" else "IBM Bob (Interviewer)"
            history_formatted += f"{sender}: {turn['text']}\n"

        prompt = f"""You are IBM Bob, a senior engineering scenario coach.
You are in the middle of a dynamic technical conversation with a candidate for a {target_role} position.
Your purpose is to play DEVIL'S ADVOCATE: challenge their decisions, ask WHY they chose that technology, point out drawbacks of their choices (e.g. latency vs cost, SQL vs NoSQL, microservices complexity), and introduce new constraints.

Conversation History so far:
{history_formatted}

Candidate's latest response:
"{candidate_response}"

Evaluate the candidate's latest response:
- If their reasoning is strong, increase the difficulty, introduce a new database or infrastructure constraint, and dig deeper.
- If their reasoning is weak, ask a simpler follow-up to check their understanding of fundamental concepts.

Provide the next conversational response. Do not give an overall evaluation score yet.
You must respond ONLY with a JSON object of the following format:
{{
  "next_question": "Your follow-up question / challenge playing Devil's Advocate",
  "difficulty": "medium",
  "topic": "system_design",
  "reasoning_focus": "tradeoffs"
}}

Do not write anything else. Return valid JSON.
"""
        response = self.client.generate(prompt)
        parsed = self._extract_json(response)
        if not parsed or "next_question" not in parsed:
            parsed = {
                "next_question": "Can you explain the trade-offs of that choice, particularly regarding consistency versus availability?",
                "difficulty": difficulty,
                "topic": "System Design",
                "reasoning_focus": "tradeoffs"
            }
        return parsed

    def evaluate_scenario(
        self,
        conversation_history: List[Dict[str, str]],
        target_role: str
    ) -> dict:
        """
        Performs the final structured AI evaluation of the candidate's engineering reasoning.
        """
        history_formatted = ""
        for turn in conversation_history:
            sender = "Candidate" if turn["sender"] == "candidate" else "IBM Bob (Interviewer)"
            history_formatted += f"{sender}: {turn['text']}\n"

        prompt = f"""You are IBM Bob, senior engineering scenario coach.
Analyze this technical scenario conversation with a candidate applying for a {target_role} role.
Rate the candidate's performance from 0 to 100 on the following attributes:
- technical_understanding: Knowledge of core CS/Engineering concepts.
- problem_solving: Logical approach to bottlenecks.
- architecture: Core system architecture selection.
- tradeoffs: Recognition of pros/cons (e.g., speed vs cost).
- scalability: Awareness of scaling limits.
- performance: Latency/throughput optimization.
- cost_awareness: Understanding of infrastructure cost.
- communication: Clarity and structure.
- decision_justification: Defending technical choices.
- overall: Overall reasoning score.

Provide lists of strengths, weaknesses, key mistakes, a better approach, concepts to revise, and next recommended practice.

Conversation History:
{history_formatted}

You must respond ONLY with a JSON object of the following format:
{{
  "evaluation": {{
    "technical_understanding": 80,
    "problem_solving": 80,
    "architecture": 80,
    "tradeoffs": 80,
    "scalability": 80,
    "performance": 80,
    "cost_awareness": 80,
    "communication": 80,
    "decision_justification": 80,
    "overall": 80
  }},
  "strengths": ["list of strengths"],
  "weaknesses": ["list of weaknesses"],
  "key_mistakes": ["key mistakes made during the chat"],
  "better_approach": "Summary of a better architecture or technical path here",
  "concepts_to_revise": ["topics to brush up on"],
  "recommendations": ["specific recommended practice actions"]
}}

Do not write anything else. Return valid JSON.
"""
        response = self.client.generate(prompt)
        parsed = self._extract_json(response)
        if not parsed or "evaluation" not in parsed:
            # Fallback mock evaluation if JSON extraction fails
            parsed = {
                "evaluation": {
                    "technical_understanding": 70,
                    "problem_solving": 75,
                    "architecture": 68,
                    "tradeoffs": 65,
                    "scalability": 70,
                    "performance": 72,
                    "cost_awareness": 60,
                    "communication": 80,
                    "decision_justification": 70,
                    "overall": 70
                },
                "strengths": ["Logical communication", "Understands database indexing principles"],
                "weaknesses": ["Vague on cache invalidation strategies", "Struggled under high-throughput constraints"],
                "key_mistakes": ["Did not account for cache stale-data race conditions"],
                "better_approach": "Introduce redis caching alongside database replica pooling",
                "concepts_to_revise": ["Cache invalidation write-through vs write-behind", "Load balancing hashing algorithms"],
                "recommendations": ["Practice scenario: DB replication setup", "Study microservices distributed transactions"]
            }
        return parsed
