from ai.agents.roadmap_agent import RoadmapAgent

agent = RoadmapAgent()

roadmap = agent.generate_roadmap(
    target_role="Backend Developer",
    current_skills="""
Python
Java
SQL
Git
Basic FastAPI
"""
)

print(roadmap)