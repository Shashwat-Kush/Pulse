import os
import time
import json
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

from groq import Groq, APIError
from logger_config import get_logger

logger = get_logger(__name__)

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "llama-3.3-70b-versatile"


def extract_topics_from_reviews(reviews: List[Dict]) -> List[Dict]:
    """
    Extract high-recall candidate topics from a list of reviews.
    """
    candidate_topics = []
    logger.info(f"Extracting topics from {len(reviews)} reviews...")
    for review in reviews:
        review_text = review.get("text", "")
        if not review_text:
            logger.debug(f"Skipping review {review.get('review_id')} - no text")
            continue

        topics = _extract_from_single_review(review_text)
        time.sleep(0.6)
        logger.debug(f"Extracted {len(topics)} topics from review {review.get('review_id')}")

        for topic in topics:
            candidate_topics.append({
                "topic_text": topic,
                "review_id": review.get("review_id"),
                "review_date": review.get("date"),
            })
    logger.info(f"Extracted {len(candidate_topics)} candidate topics total")
    return candidate_topics

def safe_extract_topics(content: str) -> list[str]:
    if not content or not content.strip():
        return []

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "topics" in parsed:
            return parsed["topics"]
    except json.JSONDecodeError:
        pass

    # Fallback: treat each non-trivial line as a topic
    return [
        line.strip("-• ").strip()
        for line in content.splitlines()
        if len(line.strip()) > 3
    ]


def _extract_from_single_review(review_text: str) -> List[str]:
    """
    Call Groq LLM to extract topics from one review.
    """
    logger.debug("Extracting topics from single review using LLM")
    prompt = _build_prompt(review_text)

    try:
        logger.debug("Calling LLM for topic extraction")
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
        logger.debug("Successfully received LLM response")

        parsed = json.loads(content)
        # topics = parsed.get("topics", [])
        # logger.debug(f"Parsed {len(topics)} topics from LLM response")
        # return topics
        return safe_extract_topics(content)

    except (APIError, json.JSONDecodeError, KeyError) as e:
        # Fail-safe: return empty list instead of crashing pipeline
        logger.warning(f"Failed to extract topics from review: {e}")
        return []


def _build_prompt(review_text: str) -> str:
    logger.debug("Building LLM prompt for review")
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
