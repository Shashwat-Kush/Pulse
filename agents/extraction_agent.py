import os
import json
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

from groq import Groq, APIError

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "llama3-70b-8192"


def extract_topics_from_reviews(reviews: List[Dict]) -> List[Dict]:
    """
    Extract high-recall candidate topics from a list of reviews.
    """
    candidate_topics = []
    print("🧠 Extracting topics from reviews...")
    for review in reviews:
        review_text = review.get("text", "")
        if not review_text:
            continue

        topics = _extract_from_single_review(review_text)

        for topic in topics:
            candidate_topics.append({
                "topic_text": topic,
                "review_id": review.get("review_id"),
                "review_date": review.get("date"),
            })
    print(f"🧠 Extracted {len(candidate_topics)} candidate topics.")
    return candidate_topics


def _extract_from_single_review(review_text: str) -> List[str]:
    """
    Call Groq LLM to extract topics from one review.
    """
    print("🧠 Extracting from single review...")
    prompt = _build_prompt(review_text)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You extract issues, complaints, and feature requests from app reviews."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=256,
        )

        content = response.choices[0].message.content

        parsed = json.loads(content)
        return parsed.get("topics", [])

    except (APIError, json.JSONDecodeError, KeyError):
        # Fail-safe: return empty list instead of crashing pipeline
        return []


def _build_prompt(review_text: str) -> str:
    print("🧠 Building prompt for review...")
    return f"""
You are analyzing a user review from a food delivery app.

Review:
\"\"\"{review_text}\"\"\"

Task:
- Extract ALL distinct issues, complaints, feature requests, or feedback.
- Use short descriptive phrases.
- Do NOT merge or normalize wording.
- Do NOT invent topics.
- If nothing meaningful exists, return an empty list.

Return ONLY valid JSON in this format:
{{
  "topics": ["string"]
}}
"""
