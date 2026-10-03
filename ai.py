from openai import OpenAI
import json

client = OpenAI(
    base_url = "http://localhost:11434/v1/",
    api_key="ollama"
)
def analyze_resume(resume_text, user_goal):
    prompt = f"""
You are a senior software engineer and hiring manager.

evaluate the resume based on the user's goal.

User goal: "{user_goal}"

STRICT RULES:
- Extract only relevant skills for tis goal
- Remove irrelevant tools [excel for backend, etc]
- Identify real gaps
- Generate roadmap only for missing fields
- Make output DIFFERENT based on goal 

Return only JSON:
{{
"skills":[],
"missing_skills":[],
"roadmap":[],
"interview_questions":[]
}}
Resume:
{resume_text}
"""
    try:
        response = client.chat.completions.create(
            model = "qwen2.5:1.5b",
            temperature=0.3,
            messages=[
                {"role": "system","content":"you're a strict hiring manager."},
                {"role": "user", "content":prompt}
            ]
        )

        content = response.choices[0].message.content.strip()

        start = content.find("{")
        end = content.rfind("}")+1

        return json.loads(content[start:end])
    except Exception as e:
        return {
            "skills":[],
            "missing_skills":[],
            "roadmap":[],
            "interview_questions":[],
            "error": str(e)

        }

