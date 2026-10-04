import os
import re
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

EMPTY = {"skills": [], "missing_skills": [], "roadmap": [], "interview_questions": []}


def extract_json(content: str) -> dict:
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()

    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Model did not return JSON. Got: {content[:200]!r}")
    return json.loads(content[start:end + 1])


def analyze_resume(resume_text, user_goal):
    # 1. Validate input before spending an API call
    if not resume_text or len(resume_text.strip()) < 50:
        return {**EMPTY, "error": "Resume text is empty or too short. Paste your resume or upload a text-based PDF/DOCX."}
    if not user_goal or not user_goal.strip():
        return {**EMPTY, "error": "Please enter the role you want to become."}

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
            max_tokens=4000,                          # room for reasoning + answer
            response_format={"type": "json_object"},  # forces valid JSON
            messages=[
                {"role": "system", "content": "You're a strict hiring manager. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        logger.info("Raw model output: %r", content)  # visible in Render logs
        return extract_json(content)

    except Exception as e:
        logger.exception("analyze_resume failed")
        return {**EMPTY, "error": str(e)}