from agents.interview_agent import InterviewAgent

agent = InterviewAgent()

question = agent.generate_question(
    role="Backend Developer",
    previous_score=72,
)

print(question)