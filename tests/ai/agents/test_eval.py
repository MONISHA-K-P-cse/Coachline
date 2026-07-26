from ai.agents.eval_agent import EvaluationAgent

agent = EvaluationAgent()

result = agent.evaluate_answer(
    question="Explain REST APIs.",
    answer="""
REST APIs are APIs that use HTTP methods like GET, POST,
PUT and DELETE to communicate between client and server.
"""
)

print(result)