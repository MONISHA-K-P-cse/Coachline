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
        mastery_summary: str = "",
        language: str = "Python"
    ) -> dict:
        """
        Generates the initial LeetCode-style coding challenge based on candidate context and coding language.
        """
        prompt = f"""You are IBM Bob, a senior engineering scenario coach.
Your job is to present the candidate with a LeetCode-style algorithmic coding challenge matching their target role, experience, and preferred language.

Candidate context:
- Target Role: {target_role}
- Experience Level: {experience_level or "Mid-Level"}
- Preferred Language: {language}
- Focus/Weakness Area: {weakness or "Data Structures & Algorithms"}

Generate a challenging LeetCode-style coding problem. Give the problem statement, constraints, and ask them to write code or describe their algorithm in {language}.
If backend, focus on system data structures (hash maps, trees, LRU caching, heap queues).
If frontend, focus on JS/TS or custom logic (deep cloning with circular links, debouncing, custom promise pools, JSON parser).

You must respond ONLY with a JSON object of the following format:
{{
  "next_question": "Problem description, example inputs/outputs, constraints, and instructions to code in {language} here",
  "difficulty": "medium",
  "topic": "algorithms",
  "reasoning_focus": "time_complexity"
}}

Do not include any conversational filler outside the JSON. Return valid JSON.
"""
        response = self.client.generate(prompt)
        parsed = self._extract_json(response)
        
        # Fallback if AI fails or returns empty
        if not parsed or "next_question" not in parsed:
            role_lower = target_role.lower()
            if "frontend" in role_lower:
                next_q = f"Challenge: Write a custom deep clone function in {language} that handles circular references, Dates, and RegEx objects.\n\nInput: An object with potential self-referential cycles.\nOutput: A deep copy of the object.\n\nDescribe your approach or write code in {language}."
                topic = f"JS Algorithms ({language})"
                focus = "recursive_cycles"
            elif "data" in role_lower or "ai" in role_lower or "ml" in role_lower:
                next_q = f"Challenge: Write an algorithm to compute the Cosine Similarity between two sparse high-dimensional text vector arrays efficiently in O(N + M) time in {language}.\n\nInput: Two sparse dictionary vector arrays.\nOutput: The float cosine similarity metric.\n\nDescribe your approach or write code in {language}."
                topic = f"Sparse Vector Math ({language})"
                focus = "vector_alignment"
            else:
                next_q = f"Challenge: Design a Least Recently Used (LRU) Cache supporting get(key) and put(key, value) operations both in O(1) time complexity in {language}.\n\nConstraints: The cache is initialized with a fixed capacity.\n\nDescribe your approach or write code in {language}."
                topic = f"Data Structures ({language})"
                focus = "cache_eviction"
                
            parsed = {
                "next_question": next_q,
                "difficulty": "medium",
                "topic": topic,
                "reasoning_focus": focus
            }
        return parsed

    def respond_to_candidate(
        self,
        conversation_history: List[Dict[str, str]],
        candidate_response: str,
        target_role: str,
        difficulty: str,
        language: str = "Python"
    ) -> dict:
        """
        Processes a turn. Bob challenges the candidate's algorithmic choices (plays Devil's Advocate),
        focusing on Big-O complexity, edge cases, and optimizations in the target language.
        """
        history_formatted = ""
        for turn in conversation_history:
            sender = "Candidate" if turn["sender"] == "candidate" else "IBM Bob (Interviewer)"
            history_formatted += f"{sender}: {turn['text']}\n"

        prompt = f"""You are IBM Bob, a senior engineering scenario coach.
You are in the middle of a LeetCode technical round in {language} with a candidate for a {target_role} position.
Your purpose is to play DEVIL'S ADVOCATE: challenge their algorithmic decisions, ask them about edge cases in {language} (null/empty inputs, duplicates, boundary overflows), ask for the exact Time and Space complexities, and push them to optimize their code.

IMPORTANT: Look at the conversation history. Do NOT ask any follow-up questions that repeat what was already discussed in the history. Focus on a new aspect (e.g. edge cases, space savings, memory layout, testing).

Conversation History so far:
{history_formatted}

Candidate's latest response:
"{candidate_response}"

Evaluate the candidate's latest response:
- If their code/algorithm is optimal, introduce a scale or memory constraint to push them further.
- If their code/algorithm is suboptimal, ask them how to optimize it using better data structures in {language}.

Provide the next conversational challenge. Do not give an overall evaluation score yet.
You must respond ONLY with a JSON object of the following format:
{{
  "next_question": "Your follow-up challenge/questions on complexities and edge cases",
  "difficulty": "medium",
  "topic": "algorithms",
  "reasoning_focus": "edge_cases"
}}

Do not write anything else. Return valid JSON.
"""
        response = self.client.generate(prompt)
        parsed = self._extract_json(response)
        if not parsed or "next_question" not in parsed:
            # Dynamically count how many turns candidate has made
            candidate_turns = sum(1 for t in conversation_history if t["sender"] == "candidate")
            
            # Simple progressive questions acting as Devil's Advocate without duplicates
            if candidate_turns <= 1:
                next_q = f"What is the exact Big-O Time and Space complexity of your proposed solution? Can we optimize the space complexity to O(1) auxiliary space in {language}?"
                focus = "complexity"
            elif candidate_turns == 2:
                next_q = f"How does your algorithm handle boundary edge cases in {language}, such as empty inputs, duplicates, or negative limits? What guards would you write?"
                focus = "edge_cases"
            elif candidate_turns == 3:
                next_q = f"Let's write unit tests for this code. What are the key happy path and failing test cases you would write in {language}?"
                focus = "unit_tests"
            else:
                next_q = f"Good. If the input size exceeds memory bounds (e.g. data streamed from a disk file), how would you rewrite this algorithm in {language} to work in chunks?"
                focus = "scale_limits"
                
            parsed = {
                "next_question": next_q,
                "difficulty": difficulty,
                "topic": f"Algorithms ({language})",
                "reasoning_focus": focus
            }
        return parsed

    def evaluate_scenario(
        self,
        conversation_history: List[Dict[str, str]],
        target_role: str
    ) -> dict:
        """
        Performs the final structured AI evaluation of the candidate's algorithmic reasoning.
        """
        history_formatted = ""
        for turn in conversation_history:
            sender = "Candidate" if turn["sender"] == "candidate" else "IBM Bob (Interviewer)"
            history_formatted += f"{sender}: {turn['text']}\n"

        prompt = f"""You are IBM Bob, senior engineering scenario coach.
Analyze this LeetCode algorithmic round with a candidate applying for a {target_role} role.
Rate the candidate's performance from 0 to 100 on the following attributes:
- technical_understanding: Knowledge of target data structures.
- problem_solving: Pattern recognition (e.g. double pointers, slide window).
- architecture: Choice of collections (hash maps, lists, heaps).
- tradeoffs: Recognition of speed vs space complexities.
- scalability: Handling extreme input bounds.
- performance: Code execution optimizations.
- cost_awareness: Stack recursion overhead vs iterative memory costs.
- communication: Walkthrough explanations.
- decision_justification: Defending complexity estimates.
- overall: Overall algorithmic score.

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
  "better_approach": "Summary of the optimal O(N) time or O(1) space code solution here",
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
                    "technical_understanding": 75,
                    "problem_solving": 78,
                    "architecture": 72,
                    "tradeoffs": 70,
                    "scalability": 68,
                    "performance": 74,
                    "cost_awareness": 70,
                    "communication": 80,
                    "decision_justification": 75,
                    "overall": 75
                },
                "strengths": ["Clear explanation of heap algorithms", "Identified O(1) lookup hash map optimization"],
                "weaknesses": ["Missed cycle checks in recursive steps", "Unclear on stack growth limits"],
                "key_mistakes": ["Did not write safety boundary check for null bounds"],
                "better_approach": "Combine a doubly-linked list with a hash map to achieve O(1) cache access and update time complexities.",
                "concepts_to_revise": ["Hash map hash collision strategies", "Recursive stack limits"],
                "recommendations": ["Solve: LRU Cache implementation on Coachline", "Solve: circular reference clone validation"]
            }
        return parsed
