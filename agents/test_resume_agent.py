from resume_agent import ResumeAgent

resume_text = """
Yashika Venugopal

Computer Science Engineering Student

Skills:
Python
Java
SQL
HTML
CSS
Git

Projects:
Expense Tracker using Python
Movie Recommendation Web App

Achievements:
9.09 CGPA
"""

agent = ResumeAgent()

result = agent.analyze_resume(resume_text)

print(result)