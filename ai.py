
import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("https://api.groq.com/openai/v1"),
    api_key=os.getenv("LLM_API_KEY"),
)
MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")


def analyze_resume(resume_text, user_goal):
    prompt = f"""
You are a senior software engineer and hiring manager.

Evaluate the resume based on the user's goal.

User goal: "{user_goal}"

STRICT RULES:
- Extract only skills relevant to this goal
- Remove irrelevant tools (e.g. Excel for a backend role)
- Identify real gaps
- Generate a roadmap only for missing skills
- Make the output DIFFERENT based on the goal

Return only JSON in this format:
{{
"skills": [],
"missing_skills": [],
"roadmap": [],
"interview_questions": []
}}

Resume:
{resume_text}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You're a strict hiring manager."},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content.strip()
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        start = content.find("{")
        end = content.rfind("}") + 1
        return json.loads(content[start:end])

    except Exception as e:
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": str(e),
        }