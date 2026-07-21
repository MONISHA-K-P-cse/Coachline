from agents.resume_agent import ResumeAgent
from agents.roadmap_agent import RoadmapAgent
from agents.notes_agent import NotesAgent
from agents.interview_agent import InterviewAgent
from agents.eval_agent import EvaluationAgent


class CoachlineOrchestrator:
    def __init__(self):
        self.resume_agent = ResumeAgent()
        self.roadmap_agent = RoadmapAgent()
        self.notes_agent = NotesAgent()
        self.interview_agent = InterviewAgent()
        self.eval_agent = EvaluationAgent()

    def run_demo(self):
        print("========== COACHLINE AI ==========\n")

        # Resume Analysis
        resume_text = """
        Python
        SQL
        FastAPI
        Git
        HTML
        CSS
        """

        resume = self.resume_agent.analyze_resume(resume_text)

        print("Resume Analysis Complete\n")

        # Roadmap
        roadmap = self.roadmap_agent.generate_roadmap(
            target_role="Backend Developer",
            current_skills=resume["summary"],
        )

        print("Roadmap Generated\n")

        # Notes
        notes = self.notes_agent.generate_notes(
            "Dynamic Programming"
        )

        print("Notes Generated\n")

        # Interview Question
        interview = self.interview_agent.generate_question(
            role="Backend Developer",
            previous_score=70,
        )

        print("Interview Question Generated\n")

        # Evaluation
        evaluation = self.eval_agent.evaluate_answer(
            interview["question"],
            """
            REST APIs use HTTP methods like
            GET, POST, PUT and DELETE.
            """,
        )

        print("Evaluation Complete\n")

        return {
            "resume": resume,
            "roadmap": roadmap,
            "notes": notes,
            "interview": interview,
            "evaluation": evaluation,
        }